## @package pcresolve.single_file_method_resolution
#  Resolve method receiver sources during single-file AST analysis.
#
#  The mixin preserves lexical visitor state on SingleFileAnalyzer while
#  isolating receiver-shape and method-source policy from AST orchestration.

import ast

from .builtin_ownership import _has_builtin_shape_method
from .ownership_contracts import (
    _has_result_owner_contract, _match_attribute_result_owner,
)
from .scope import SCOPE_MODULE
from .sources import (
    CallResult, DerivedResult, InstanceAttribute, InstanceMethod,
    ParameterSource, PythonShape, SuperMethod, UnknownSource,
    is_structured_source, normalize_source,
)


## Resolve method receiver sources using SingleFileAnalyzer state.
class SingleFileMethodResolutionMixin:
    ## Attempt to resolve an instance method call to a class member.
    #
    #  Handles self.method(), known_object.method(), and chained attribute calls.
    #  @param node The Call AST node.
    #  @return Method name, structured ("instance_method", ...) tuple, or None.
    def _resolve_methods(self, node):
        if not isinstance(node, ast.Call):
            return None
        func = node.func
        if not isinstance(func, ast.Attribute):
            return None
        re = func.value
        method_name = func.attr
        # Preserve a parameter-derived expression as the receiver source.
        # Cross-file resolution may prove a single owner from all operands;
        # without this structured source, get_base() falls back to the first
        # operand and can incorrectly classify the call as local.
        if isinstance(re, (ast.BinOp, ast.UnaryOp, ast.Compare)):
            parameter_dependency = self._parameter_dependency_source(re)
            def contains_bounded_source(source):
                source = normalize_source(source)
                if isinstance(source, (ParameterSource, InstanceAttribute)):
                    return True
                if isinstance(source, DerivedResult):
                    return any(contains_bounded_source(item)
                               for item in source.sources)
                if isinstance(source, CallResult):
                    return contains_bounded_source(source.result_source)
                return False

            if (isinstance(parameter_dependency, DerivedResult)
                    and contains_bounded_source(parameter_dependency)):
                return InstanceMethod(parameter_dependency, method_name)
            if isinstance(re, (ast.BinOp, ast.UnaryOp)):
                expression_top = self._expr_receiver_top(re)
                if expression_top not in (
                        None, "", "local", "python", "unknown"):
                    return InstanceMethod(expression_top, method_name)
                external_tops = {
                    top for top in self._operator_operand_tops(re)
                    if top not in (None, "", "local", "python", "unknown")
                }
                if external_tops or parameter_dependency is not None:
                    return InstanceMethod(
                        UnknownSource("unresolved operator result owner"),
                        method_name,
                    )
        receiver_kind, _ = self._expression_container_shape(re)
        if receiver_kind:
            if _has_builtin_shape_method(receiver_kind, method_name):
                return InstanceMethod("python", method_name)
            return InstanceMethod(
                UnknownSource(
                    "unsupported %s protocol" % receiver_kind),
                method_name,
            )

        ## 1.0.5 P2: super().method() — capture enclosing class context
        #  while _class_stack is still available during AST visit.
        if isinstance(re, ast.Call):
            if isinstance(re.func, ast.Name) and re.func.id == "super":
                if self._class_stack:
                    class_key = self._class_stack[-1]
                    class_qualname = ".".join(self._class_stack)
                    return SuperMethod(class_key, class_qualname, method_name)
                return InstanceMethod("super", method_name)

            if (isinstance(re.func, ast.Name)
                    and method_name in self.class_methods.get(
                        re.func.id, ())):
                return InstanceMethod(re.func.id, method_name)

            inner_result = normalize_source(self.trace_source(re))
            if isinstance(inner_result, CallResult):
                inner_owner = normalize_source(inner_result.result_source)
                if isinstance(inner_owner, str):
                    return InstanceMethod(inner_owner, method_name)
                if isinstance(inner_owner, UnknownSource):
                    return InstanceMethod(inner_owner, method_name)

            explicit_owner = self._explicit_external_receiver_top(re)
            if explicit_owner not in (None, "", "local", "python", "unknown"):
                return InstanceMethod(explicit_owner, method_name)

            # A direct chained method belongs to the object explicitly
            # returned by a project-local method.  Gate this path on local
            # method identity so direct library calls such as np.log(...)
            # continue through receiver-preserving return rules below.
            inner_method = self._resolve_methods(re)
            if (isinstance(inner_method, InstanceMethod)
                    and isinstance(
                        normalize_source(inner_method.receiver),
                        UnknownSource)):
                return InstanceMethod(
                    inner_method.receiver, method_name)
            local_method = False
            if (isinstance(inner_method, InstanceMethod)
                    and isinstance(inner_method.receiver, str)):
                local_method = inner_method.receiver in self.class_methods
                if not local_method:
                    binding = self.current_scope().lookup(
                        inner_method.receiver)
                    if binding is not None:
                        binding_source = normalize_source(binding.source)
                        if (isinstance(binding_source, CallResult)
                                and isinstance(binding_source.callee, str)):
                            local_method = (
                                binding_source.callee in self.class_methods)
            if local_method:
                result_source = normalize_source(self.trace_source(re))
                if isinstance(result_source, CallResult):
                    if (isinstance(result_source.callee, str)
                            and result_source.callee in self.return_sources):
                        return InstanceMethod(result_source, method_name)
                    candidate = result_source.result_source
                    if not isinstance(candidate, str):
                        candidate = result_source.callee
                    if isinstance(candidate, str):
                        candidate_top = self.symbols.get_top(candidate)
                        if candidate_top not in (
                                None, "", "local", "python", "unknown"):
                            return InstanceMethod(candidate, method_name)
            if (isinstance(inner_method, InstanceMethod)
                    and _has_result_owner_contract(
                        inner_method.method)):
                result = CallResult(
                    inner_method,
                    display_name=ast.unparse(re.func),
                    call_lineno=re.lineno,
                    call_col_offset=re.col_offset,
                    result_source=DerivedResult(
                        "method_result",
                        (inner_method,),
                        inner_method.method,
                    ),
                )
                return InstanceMethod(result, method_name)

        def _lookup_instance_attr(attr_name):
            if self._class_stack:
                class_name = self._class_stack[-1]
                if (class_name, attr_name) in self.instance_attrs:
                    return self.instance_attrs[(class_name, attr_name)]
            return self.symbols.direct.get(attr_name)

        def _resolve_on_class(class_name, receiver_key):
            if not class_name:
                return None
            methods = self.class_methods.get(class_name, [])
            if methods and method_name in methods:
                return InstanceMethod(receiver_key, method_name)
            inherited_owner = self._inherited_builtin_method_owner(
                class_name, method_name)
            if inherited_owner == "local":
                return InstanceMethod(receiver_key, method_name)
            if inherited_owner is not None:
                return InstanceMethod(inherited_owner, method_name)
            if class_name in self.class_methods:
                return InstanceMethod(receiver_key, method_name)
            if class_name in self.import_from_symbols:
                return InstanceMethod(class_name, method_name)
            return None

        def _parameter_method(receiver, parameter_name):
            if not self._caller_stack:
                return None
            binding = self.current_scope().lookup(
                parameter_name, skip_parent_classes=True)
            if (binding is None
                    or binding.binding_kind != "parameter"):
                return None
            scope_name = self._caller_stack[-1].qualname
            params = self.function_params.get(scope_name)
            if params is None:
                params = self.function_params.get(
                    scope_name.rsplit(".", 1)[-1], [])
            if parameter_name not in params:
                return None
            return InstanceMethod(
                receiver,
                method_name,
                parameter_scope=scope_name,
                parameter_name=parameter_name,
            )

        if isinstance(re, ast.Name):
            for guards in reversed(self._receiver_owner_guards):
                guarded_owner = guards.get(re.id)
                if guarded_owner is not None:
                    if isinstance(guarded_owner, PythonShape):
                        if _has_builtin_shape_method(
                                guarded_owner.kind, method_name):
                            return InstanceMethod("python", method_name)
                        return InstanceMethod(
                            UnknownSource(
                                "unsupported %s protocol"
                                % guarded_owner.kind),
                            method_name,
                        )
                    return InstanceMethod(guarded_owner, method_name)
            if re.id == "self" and self._class_stack:
                cn = self._class_stack[-1]
                return _resolve_on_class(cn, cn)
            # Lexical parameter identity takes precedence over the legacy
            # module compatibility table.  A same-named assignment in
            # another scope must not erase the call edge that can establish
            # this receiver's owner.
            parameter = _parameter_method(re.id, re.id)
            if parameter is not None:
                return parameter
            class_name = self.symbols.direct.get(re.id)
            class_name = normalize_source(class_name)
            if isinstance(class_name, CallResult):
                if isinstance(
                        normalize_source(class_name.result_source),
                        (str, UnknownSource)):
                    return InstanceMethod(class_name, method_name)
                class_name = class_name.callee
            # 1.0.5 P1: treat "local" class_name the same as
            # absent — still create InstanceMethod so the
            # builtin container method check applies.
            if not class_name or class_name == "local":
                binding = self.current_scope().lookup(re.id)
                if binding is not None:
                    src_norm = normalize_source(binding.source)
                    if isinstance(src_norm, ParameterSource):
                        if src_norm.derived:
                            return InstanceMethod(src_norm, method_name)
                        else:
                            receiver = ".".join(
                                (src_norm.name,) + src_norm.attributes)
                        return InstanceMethod(
                            receiver, method_name,
                            parameter_scope=src_norm.scope,
                            parameter_name=src_norm.name)
                    if (isinstance(src_norm, str)
                            and src_norm in
                            self.homogeneous_container_value_sources):
                        return InstanceMethod(
                            self.homogeneous_container_value_sources[
                                src_norm], method_name)
                    if binding.source == "local":
                        return InstanceMethod(re.id, method_name)
                    if isinstance(src_norm, CallResult):
                        cn = src_norm.callee
                        if isinstance(cn, str) and cn in self.class_methods:
                            return _resolve_on_class(cn, cn)
                        if isinstance(cn, str) and cn in self.import_from_symbols:
                            return InstanceMethod(cn, method_name)
                        return InstanceMethod(src_norm, method_name)
                    if is_structured_source(src_norm):
                        return InstanceMethod(src_norm, method_name)
                    if (isinstance(src_norm, str)
                            and binding.binding_kind != "import"
                            and src_norm not in (
                                "", "local", "python", "unknown")):
                        return InstanceMethod(src_norm, method_name)
                # Module-level local bindings — scope lookup
                # may return None at module scope; fall back
                # to the direct symbol table.
                if self.symbols.direct.get(re.id) == "local":
                    return InstanceMethod(re.id, method_name)
                return None
            return _resolve_on_class(class_name, re.id)

        # Preserve a parameter receiver when an item is selected before the
        # method call, e.g. values[0].reshape(...).  The item may have a
        # different runtime type from the container, so retain the parameter
        # edge and let cross_file resolve its unique call-site owner.
        if isinstance(re, ast.Subscript):
            container_dependency = self._parameter_dependency_source(
                re.value)
            if (isinstance(re.value, ast.Attribute)
                    and isinstance(container_dependency, ParameterSource)
                    and container_dependency.attributes):
                return InstanceMethod(
                    UnknownSource(
                        "item of parameter runtime attribute"),
                    method_name,
                )
            dependency = self._parameter_dependency_source(re)
            if isinstance(dependency, ParameterSource):
                if dependency.derived_operation == "slice":
                    return InstanceMethod(dependency, method_name)
                return InstanceMethod(
                    dependency.name,
                    method_name,
                    parameter_scope=dependency.scope,
                    parameter_name=dependency.name,
                )
            if isinstance(dependency, UnknownSource):
                return InstanceMethod(dependency, method_name)
            receiver_top = None
            if self._is_instance_field_expression(re.value):
                receiver_top = self._explicit_external_receiver_top(re.value)
            if receiver_top not in (None, "", "local", "python", "unknown"):
                return InstanceMethod(receiver_top, method_name)

        if isinstance(re, ast.Attribute):
            attribute_receiver_top = self._expr_receiver_top(re.value)
            attribute_owner = _match_attribute_result_owner(
                attribute_receiver_top, re.attr)
            if attribute_owner is not None:
                return InstanceMethod(attribute_owner, method_name)
            receiver_name = self._attribute_name(re)
            if (self._import_attribute_key(re) in
                    self._subscripted_import_attribute_receivers):
                return InstanceMethod(
                    UnknownSource(
                        "runtime attribute with subscript protocol"),
                    method_name,
                )
            if receiver_name:
                receiver_binding = self.current_scope().lookup(
                    receiver_name, skip_parent_classes=True)
                if (receiver_binding is not None
                        and receiver_binding.source == "python"):
                    return InstanceMethod("python", method_name)
            chain = self._attribute_chain_list(re)
            if chain:
                if chain[0] == "self" and self._class_stack:
                    cn = self._class_stack[-1]
                    attr_name = "self." + ".".join(chain[1:])
                    result = _resolve_on_class(cn, cn)
                    if isinstance(normalize_source(result), InstanceMethod):
                        if attr_name == "self.__dict__":
                            if _has_builtin_shape_method(
                                    "dict", method_name):
                                return InstanceMethod("python", method_name)
                            return InstanceMethod(
                                UnknownSource(
                                    "unsupported dict protocol"),
                                method_name,
                            )
                        attr_source = _lookup_instance_attr(attr_name)
                        attr_source = normalize_source(attr_source)
                        if isinstance(attr_source, ParameterSource):
                            receiver = ".".join(
                                (attr_source.name,) + attr_source.attributes)
                            return InstanceMethod(
                                receiver,
                                method_name,
                                parameter_scope=attr_source.scope,
                                parameter_name=attr_source.name)
                        if isinstance(attr_source, CallResult):
                            callee = attr_source.callee
                            if not isinstance(callee, str):
                                return InstanceMethod(
                                    attr_source, method_name)
                            callee_parts = callee.rsplit(".", 1)
                            is_local_method_result = (
                                len(callee_parts) == 2
                                and callee_parts[0] in self.class_methods
                                and callee_parts[1] in self.class_methods[
                                    callee_parts[0]]
                            )
                            if (callee in self.return_sources
                                    or is_local_method_result):
                                return InstanceMethod(
                                    attr_source, method_name)
                            if ('.' not in callee
                                    and (callee in self.symbols.direct
                                         or callee in self.import_from_symbols
                                         or any(
                                             alias == callee
                                             or alias.startswith(callee + ".")
                                             for alias in self.import_aliases))):
                                return InstanceMethod(callee, method_name)
                            if '.' in callee:
                                prefix = callee.split('.')[0]
                                prefix_is_origin = any(
                                    isinstance(v, str)
                                    and (v == prefix
                                         or v.startswith(prefix + "."))
                                    for v in self.symbols.direct.values())
                                if prefix_is_origin:
                                    return InstanceMethod(prefix, method_name)
                                if prefix in self.import_from_symbols:
                                    return InstanceMethod(prefix, method_name)
                                if prefix in self.symbols.direct:
                                    return InstanceMethod(prefix, method_name)
                                return InstanceMethod(callee, method_name)
                            wildcard_owner = (
                                self._unique_wildcard_import_owner())
                            if wildcard_owner is not None:
                                return InstanceMethod(
                                    wildcard_owner, method_name)
                        if (isinstance(attr_source, str)
                                and '.' not in attr_source
                                and attr_source in self.symbols.direct):
                            return InstanceMethod(attr_source, method_name)
                        if isinstance(attr_source, str) and attr_source != "local":
                            return InstanceMethod(attr_source, method_name)
                    scope_name = (
                        self._caller_stack[-1].qualname
                        if self._caller_stack else "")
                    return InstanceMethod(
                        InstanceAttribute(cn, attr_name, scope_name),
                        method_name,
                    )
                root = chain[0]
                root_binding = self.current_scope().lookup(
                    root, skip_parent_classes=True)
                if (root_binding is not None
                        and root_binding.binding_kind == "import"
                        and root_binding.scope_kind != SCOPE_MODULE):
                    return InstanceMethod(root_binding.source, method_name)
                if root in self.import_from_symbols:
                    return InstanceMethod(root, method_name)
                root_src = self.symbols.direct.get(root)
                root_src = normalize_source(root_src)
                if isinstance(root_src, CallResult):
                    root_src = root_src.callee
                if root_src in self.import_from_symbols:
                    return InstanceMethod(root_src, method_name)
                field_source = None
                for scope_key in self._local_instance_field_scope_keys(root):
                    field_source = self._local_instance_field_sources.get(
                        (scope_key, root, ".".join(chain[1:])))
                    if field_source is not None:
                        break
                if field_source is not None:
                    field_top = self._structured_source_owner_top(field_source)
                    if field_top not in (
                            None, "", "local", "python", "unknown"):
                        return InstanceMethod(field_top, method_name)
                # P0: resolve instance attributes for non-self receivers
                # whose root traces to a local class instance.
                # e.g. client.backend.loads() where client=Client()
                # and self.backend=json  →  trace client.backend
                # through instance_attrs to find json, then
                # classify loads as json.loads.
                target_class = root_src
                if not target_class:
                    binding = self.current_scope().lookup(root)
                    if binding is not None:
                        target_class = normalize_source(binding.source)
                        if isinstance(target_class, CallResult):
                            target_class = target_class.callee
                        if target_class == "local":
                            parameter = _parameter_method(
                                ".".join(chain), root)
                            if parameter is not None:
                                return parameter
                if isinstance(target_class, str) and target_class in self.class_methods:
                    if len(chain) >= 2:
                        attr_name = "self." + ".".join(chain[1:])
                        attr_source = self.instance_attrs.get(
                            (target_class, attr_name))
                        attr_source = normalize_source(attr_source)
                        if isinstance(attr_source, CallResult):
                            callee = attr_source.callee
                            if isinstance(callee, str):
                                return InstanceMethod(callee, method_name)
                        if (isinstance(attr_source, str)
                                and attr_source not in (
                                    "local", "python", "unknown", "")):
                            return InstanceMethod(attr_source, method_name)
                    return _resolve_on_class(target_class, root)
        if isinstance(re, ast.Constant):
            # Literal constant method call: "str".format() → python.
            # The receiver is a literal Python builtin type, so the
            # method callable is always python.
            if isinstance(re.value, str):
                return InstanceMethod("str", method_name)
            if isinstance(re.value, bytes):
                return InstanceMethod("bytes", method_name)
        if (isinstance(re, ast.Subscript)
                and isinstance(re.value, ast.Call)):
            item_owner = self._resolve_call_result_item_owner(re.value)
            if item_owner is not None:
                return InstanceMethod(item_owner, method_name)
        if isinstance(re, ast.Compare):
            result = self._resolve_compare_result_top(re, method_name)
            if result is not None:
                return result
            # Owner could not be resolved — still collect the call
            # so it isn't silently dropped.  The cross-file resolver
            # will treat it conservatively.
            return InstanceMethod("__unresolved_compare__", method_name)
        return None
