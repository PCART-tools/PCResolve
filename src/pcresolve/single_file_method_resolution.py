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
        if not isinstance(node.func, ast.Attribute):
            return None
        receiver = node.func.value
        method_name = node.func.attr
        result = self._operator_receiver_method_source(
            receiver, method_name)
        if result is not None:
            return result
        receiver_kind, _ = self._expression_container_shape(receiver)
        if receiver_kind:
            return self._container_receiver_method_source(
                receiver_kind, method_name)
        if isinstance(receiver, ast.Call):
            return self._call_receiver_method_source(receiver, method_name)
        if isinstance(receiver, ast.Name):
            return self._name_receiver_method_source(receiver, method_name)
        if isinstance(receiver, ast.Subscript):
            result = self._subscript_receiver_method_source(
                receiver, method_name)
            if result is not None:
                return result
        if isinstance(receiver, ast.Attribute):
            return self._attribute_receiver_method_source(
                receiver, method_name)
        if isinstance(receiver, ast.Constant):
            return self._constant_receiver_method_source(
                receiver, method_name)
        if isinstance(receiver, ast.Compare):
            result = self._resolve_compare_result_top(
                receiver, method_name)
            if result is not None:
                return result
            return InstanceMethod("__unresolved_compare__", method_name)
        return None

    ## Resolve operator and comparison receiver ownership evidence.
    def _operator_receiver_method_source(self, receiver, method_name):
        if not isinstance(receiver, (ast.BinOp, ast.UnaryOp, ast.Compare)):
            return None
        dependency = self._parameter_dependency_source(receiver)
        if (isinstance(dependency, DerivedResult)
                and self._contains_bounded_method_source(dependency)):
            return InstanceMethod(dependency, method_name)
        if not isinstance(receiver, (ast.BinOp, ast.UnaryOp)):
            return None
        expression_top = self._expr_receiver_top(receiver)
        if expression_top not in (
                None, "", "local", "python", "unknown"):
            return InstanceMethod(expression_top, method_name)
        external_tops = {
            top for top in self._operator_operand_tops(receiver)
            if top not in (None, "", "local", "python", "unknown")
        }
        if external_tops or dependency is not None:
            return InstanceMethod(
                UnknownSource("unresolved operator result owner"),
                method_name)
        return None

    ## Return whether a structured source contains bounded receiver evidence.
    def _contains_bounded_method_source(self, source):
        source = normalize_source(source)
        if isinstance(source, (ParameterSource, InstanceAttribute)):
            return True
        if isinstance(source, DerivedResult):
            return any(
                self._contains_bounded_method_source(item)
                for item in source.sources)
        if isinstance(source, CallResult):
            return self._contains_bounded_method_source(
                source.result_source)
        return False

    ## Resolve methods on a proven builtin container shape.
    def _container_receiver_method_source(self, receiver_kind, method_name):
        if _has_builtin_shape_method(receiver_kind, method_name):
            return InstanceMethod("python", method_name)
        return InstanceMethod(
            UnknownSource("unsupported %s protocol" % receiver_kind),
            method_name)

    ## Resolve a method invoked on the result of another call.
    def _call_receiver_method_source(self, receiver, method_name):
        if isinstance(receiver.func, ast.Name) and receiver.func.id == "super":
            if self._class_stack:
                class_key = self._class_stack[-1]
                class_qualname = ".".join(self._class_stack)
                return SuperMethod(class_key, class_qualname, method_name)
            return InstanceMethod("super", method_name)
        if (isinstance(receiver.func, ast.Name)
                and method_name in self.class_methods.get(
                    receiver.func.id, ())):
            return InstanceMethod(receiver.func.id, method_name)
        inner_result = normalize_source(self.trace_source(receiver))
        if isinstance(inner_result, CallResult):
            inner_owner = normalize_source(inner_result.result_source)
            if isinstance(inner_owner, (str, UnknownSource)):
                return InstanceMethod(inner_owner, method_name)
        explicit_owner = self._explicit_external_receiver_top(receiver)
        if explicit_owner not in (None, "", "local", "python", "unknown"):
            return InstanceMethod(explicit_owner, method_name)
        inner_method = self._resolve_methods(receiver)
        if (isinstance(inner_method, InstanceMethod)
                and isinstance(
                    normalize_source(inner_method.receiver), UnknownSource)):
            return InstanceMethod(inner_method.receiver, method_name)
        if self._is_local_inner_method(inner_method):
            result = self._local_call_result_method_source(
                receiver, method_name)
            if result is not None:
                return result
        if (isinstance(inner_method, InstanceMethod)
                and _has_result_owner_contract(inner_method.method)):
            result = CallResult(
                inner_method,
                display_name=ast.unparse(receiver.func),
                call_lineno=receiver.lineno,
                call_col_offset=receiver.col_offset,
                result_source=DerivedResult(
                    "method_result", (inner_method,), inner_method.method),
            )
            return InstanceMethod(result, method_name)
        return None

    ## Return whether a chained receiver is a known project-local method.
    def _is_local_inner_method(self, inner_method):
        if (not isinstance(inner_method, InstanceMethod)
                or not isinstance(inner_method.receiver, str)):
            return False
        if inner_method.receiver in self.class_methods:
            return True
        binding = self.current_scope().lookup(inner_method.receiver)
        if binding is None:
            return False
        binding_source = normalize_source(binding.source)
        return (isinstance(binding_source, CallResult)
                and isinstance(binding_source.callee, str)
                and binding_source.callee in self.class_methods)

    ## Resolve the explicit object returned by a project-local method.
    def _local_call_result_method_source(self, receiver, method_name):
        result_source = normalize_source(self.trace_source(receiver))
        if not isinstance(result_source, CallResult):
            return None
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
        return None

    ## Look up one instance attribute in class or legacy symbol state.
    def _lookup_method_instance_attr(self, attr_name):
        if self._class_stack:
            class_name = self._class_stack[-1]
            if (class_name, attr_name) in self.instance_attrs:
                return self.instance_attrs[(class_name, attr_name)]
        return self.symbols.direct.get(attr_name)

    ## Resolve one method against a local or imported class identity.
    def _resolve_method_on_class(
            self, class_name, receiver_key, method_name):
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

    ## Preserve lexical parameter identity on a method receiver.
    def _parameter_receiver_method_source(
            self, receiver, parameter_name, method_name):
        if not self._caller_stack:
            return None
        binding = self.current_scope().lookup(
            parameter_name, skip_parent_classes=True)
        if binding is None or binding.binding_kind != "parameter":
            return None
        scope_name = self._caller_stack[-1].qualname
        params = self.function_params.get(scope_name)
        if params is None:
            params = self.function_params.get(
                scope_name.rsplit(".", 1)[-1], [])
        if parameter_name not in params:
            return None
        return InstanceMethod(
            receiver, method_name,
            parameter_scope=scope_name,
            parameter_name=parameter_name)

    ## Resolve a simple-name method receiver.
    def _name_receiver_method_source(self, receiver, method_name):
        guarded = self._guarded_receiver_method_source(
            receiver.id, method_name)
        if guarded is not None:
            return guarded
        if receiver.id == "self" and self._class_stack:
            class_name = self._class_stack[-1]
            return self._resolve_method_on_class(
                class_name, class_name, method_name)
        parameter = self._parameter_receiver_method_source(
            receiver.id, receiver.id, method_name)
        if parameter is not None:
            return parameter
        class_name = normalize_source(self.symbols.direct.get(receiver.id))
        if isinstance(class_name, CallResult):
            if isinstance(
                    normalize_source(class_name.result_source),
                    (str, UnknownSource)):
                return InstanceMethod(class_name, method_name)
            class_name = class_name.callee
        if not class_name or class_name == "local":
            binding = self.current_scope().lookup(receiver.id)
            result = self._binding_receiver_method_source(
                receiver.id, binding, method_name)
            if result is not None:
                return result
            if self.symbols.direct.get(receiver.id) == "local":
                return InstanceMethod(receiver.id, method_name)
            return None
        return self._resolve_method_on_class(
            class_name, receiver.id, method_name)

    ## Resolve receiver ownership narrowed by a finite guard.
    def _guarded_receiver_method_source(self, receiver_name, method_name):
        for guards in reversed(self._receiver_owner_guards):
            guarded_owner = guards.get(receiver_name)
            if guarded_owner is None:
                continue
            if isinstance(guarded_owner, PythonShape):
                return self._container_receiver_method_source(
                    guarded_owner.kind, method_name)
            return InstanceMethod(guarded_owner, method_name)
        return None

    ## Resolve a lexical binding used as a simple-name receiver.
    def _binding_receiver_method_source(
            self, receiver_name, binding, method_name):
        if binding is None:
            return None
        source = normalize_source(binding.source)
        if isinstance(source, ParameterSource):
            if source.derived:
                return InstanceMethod(source, method_name)
            receiver = ".".join((source.name,) + source.attributes)
            return InstanceMethod(
                receiver, method_name,
                parameter_scope=source.scope,
                parameter_name=source.name)
        if (isinstance(source, str)
                and source in self.homogeneous_container_value_sources):
            return InstanceMethod(
                self.homogeneous_container_value_sources[source],
                method_name)
        if binding.source == "local":
            return InstanceMethod(receiver_name, method_name)
        if isinstance(source, CallResult):
            class_name = source.callee
            if isinstance(class_name, str) and class_name in self.class_methods:
                return self._resolve_method_on_class(
                    class_name, class_name, method_name)
            if (isinstance(class_name, str)
                    and class_name in self.import_from_symbols):
                return InstanceMethod(class_name, method_name)
            return InstanceMethod(source, method_name)
        if is_structured_source(source):
            return InstanceMethod(source, method_name)
        if (isinstance(source, str)
                and binding.binding_kind != "import"
                and source not in ("", "local", "python", "unknown")):
            return InstanceMethod(source, method_name)
        return None

    ## Resolve a method receiver selected through a subscript.
    def _subscript_receiver_method_source(self, receiver, method_name):
        container_dependency = self._parameter_dependency_source(
            receiver.value)
        if (isinstance(receiver.value, ast.Attribute)
                and isinstance(container_dependency, ParameterSource)
                and container_dependency.attributes):
            return InstanceMethod(
                UnknownSource("item of parameter runtime attribute"),
                method_name)
        dependency = self._parameter_dependency_source(receiver)
        if isinstance(dependency, ParameterSource):
            if dependency.derived_operation == "slice":
                return InstanceMethod(dependency, method_name)
            return InstanceMethod(
                dependency.name, method_name,
                parameter_scope=dependency.scope,
                parameter_name=dependency.name)
        if isinstance(dependency, UnknownSource):
            return InstanceMethod(dependency, method_name)
        receiver_top = None
        if self._is_instance_field_expression(receiver.value):
            receiver_top = self._explicit_external_receiver_top(
                receiver.value)
        if receiver_top not in (None, "", "local", "python", "unknown"):
            return InstanceMethod(receiver_top, method_name)
        if isinstance(receiver.value, ast.Call):
            item_owner = self._resolve_call_result_item_owner(receiver.value)
            if item_owner is not None:
                return InstanceMethod(item_owner, method_name)
        return None

    ## Resolve a dotted attribute method receiver.
    def _attribute_receiver_method_source(self, receiver, method_name):
        attribute_receiver_top = self._expr_receiver_top(receiver.value)
        attribute_owner = _match_attribute_result_owner(
            attribute_receiver_top, receiver.attr)
        if attribute_owner is not None:
            return InstanceMethod(attribute_owner, method_name)
        receiver_name = self._attribute_name(receiver)
        if (self._import_attribute_key(receiver) in
                self._subscripted_import_attribute_receivers):
            return InstanceMethod(
                UnknownSource("runtime attribute with subscript protocol"),
                method_name)
        if receiver_name:
            binding = self.current_scope().lookup(
                receiver_name, skip_parent_classes=True)
            if binding is not None and binding.source == "python":
                return InstanceMethod("python", method_name)
        chain = self._attribute_chain_list(receiver)
        if not chain:
            return None
        if chain[0] == "self" and self._class_stack:
            return self._self_attribute_method_source(chain, method_name)
        return self._named_attribute_method_source(chain, method_name)

    ## Resolve a method invoked through an enclosing instance attribute.
    def _self_attribute_method_source(self, chain, method_name):
        class_name = self._class_stack[-1]
        attr_name = "self." + ".".join(chain[1:])
        class_result = self._resolve_method_on_class(
            class_name, class_name, method_name)
        if isinstance(normalize_source(class_result), InstanceMethod):
            if attr_name == "self.__dict__":
                return self._container_receiver_method_source(
                    "dict", method_name)
            attr_source = normalize_source(
                self._lookup_method_instance_attr(attr_name))
            result = self._instance_attribute_method_source(
                attr_source, method_name)
            if result is not None:
                return result
        scope_name = (
            self._caller_stack[-1].qualname if self._caller_stack else "")
        return InstanceMethod(
            InstanceAttribute(class_name, attr_name, scope_name),
            method_name)

    ## Resolve a stored self attribute's method receiver source.
    def _instance_attribute_method_source(self, source, method_name):
        if isinstance(source, ParameterSource):
            receiver = ".".join((source.name,) + source.attributes)
            return InstanceMethod(
                receiver, method_name,
                parameter_scope=source.scope,
                parameter_name=source.name)
        if isinstance(source, CallResult):
            result = self._attribute_call_result_method_source(
                source, method_name)
            if result is not None:
                return result
        if (isinstance(source, str)
                and "." not in source
                and source in self.symbols.direct):
            return InstanceMethod(source, method_name)
        if isinstance(source, str) and source != "local":
            return InstanceMethod(source, method_name)
        return None

    ## Resolve a CallResult stored in an instance attribute.
    def _attribute_call_result_method_source(self, source, method_name):
        callee = source.callee
        if not isinstance(callee, str):
            return InstanceMethod(source, method_name)
        callee_parts = callee.rsplit(".", 1)
        is_local_method_result = (
            len(callee_parts) == 2
            and callee_parts[0] in self.class_methods
            and callee_parts[1] in self.class_methods[callee_parts[0]])
        if callee in self.return_sources or is_local_method_result:
            return InstanceMethod(source, method_name)
        if ("." not in callee
                and (callee in self.symbols.direct
                     or callee in self.import_from_symbols
                     or any(alias == callee
                            or alias.startswith(callee + ".")
                            for alias in self.import_aliases))):
            return InstanceMethod(callee, method_name)
        if "." in callee:
            prefix = callee.split(".")[0]
            prefix_is_origin = any(
                isinstance(value, str)
                and (value == prefix or value.startswith(prefix + "."))
                for value in self.symbols.direct.values())
            if (prefix_is_origin
                    or prefix in self.import_from_symbols
                    or prefix in self.symbols.direct):
                return InstanceMethod(prefix, method_name)
            return InstanceMethod(callee, method_name)
        wildcard_owner = self._unique_wildcard_import_owner()
        if wildcard_owner is not None:
            return InstanceMethod(wildcard_owner, method_name)
        return None

    ## Resolve a method receiver rooted at a non-self dotted name.
    def _named_attribute_method_source(self, chain, method_name):
        root = chain[0]
        root_binding = self.current_scope().lookup(
            root, skip_parent_classes=True)
        if (root_binding is not None
                and root_binding.binding_kind == "import"
                and root_binding.scope_kind != SCOPE_MODULE):
            return InstanceMethod(root_binding.source, method_name)
        if root in self.import_from_symbols:
            return InstanceMethod(root, method_name)
        root_source = normalize_source(self.symbols.direct.get(root))
        if isinstance(root_source, CallResult):
            root_source = root_source.callee
        if root_source in self.import_from_symbols:
            return InstanceMethod(root_source, method_name)
        field_source = self._local_field_method_source(
            root, chain, method_name)
        if field_source is not None:
            return field_source
        target_class = root_source
        if not target_class:
            binding = self.current_scope().lookup(root)
            if binding is not None:
                target_class = normalize_source(binding.source)
                if isinstance(target_class, CallResult):
                    target_class = target_class.callee
                if target_class == "local":
                    parameter = self._parameter_receiver_method_source(
                        ".".join(chain), root, method_name)
                    if parameter is not None:
                        return parameter
        if (isinstance(target_class, str)
                and target_class in self.class_methods):
            return self._local_class_attribute_method_source(
                target_class, root, chain, method_name)
        return None

    ## Resolve a local-instance field source recorded for one lexical scope.
    def _local_field_method_source(self, root, chain, method_name):
        field_source = None
        for scope_key in self._local_instance_field_scope_keys(root):
            field_source = self._local_instance_field_sources.get(
                (scope_key, root, ".".join(chain[1:])))
            if field_source is not None:
                break
        if field_source is None:
            return None
        field_top = self._structured_source_owner_top(field_source)
        if field_top in (None, "", "local", "python", "unknown"):
            return None
        return InstanceMethod(field_top, method_name)

    ## Resolve an attribute on a receiver proven to be a local class.
    def _local_class_attribute_method_source(
            self, class_name, root, chain, method_name):
        if len(chain) >= 2:
            attr_name = "self." + ".".join(chain[1:])
            attr_source = normalize_source(
                self.instance_attrs.get((class_name, attr_name)))
            if (isinstance(attr_source, CallResult)
                    and isinstance(attr_source.callee, str)):
                return InstanceMethod(attr_source.callee, method_name)
            if (isinstance(attr_source, str)
                    and attr_source not in (
                        "local", "python", "unknown", "")):
                return InstanceMethod(attr_source, method_name)
        return self._resolve_method_on_class(
            class_name, root, method_name)

    ## Resolve a method on a literal constant receiver.
    def _constant_receiver_method_source(self, receiver, method_name):
        if isinstance(receiver.value, str):
            return InstanceMethod("str", method_name)
        if isinstance(receiver.value, bytes):
            return InstanceMethod("bytes", method_name)
        return None
