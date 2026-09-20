## @package pcresolve.single_file_receiver_resolution
#  Resolve receiver, callable, and bounded result ownership in one file.
#
#  The mixin operates on SingleFileAnalyzer lexical state and preserves
#  receiver-resolution order without owning a second analysis state.

import ast

from .builtin_ownership import _BUILTIN_CONTAINER_METHODS
from .ownership_contracts import (
    _COMPARE_RESULT_METHODS, _CONVERSION_ATTRIBUTE_TARGETS,
    _CONVERSION_METHOD_TARGETS, _RECEIVER_PRESERVE_UFUNCS,
    _match_result_item_owner, _match_result_owner,
)
from .single_file_container_shapes import _container_kind
from .sources import (
    CallResult, DerivedResult, InstanceAttribute, InstanceMethod,
    ParameterSource, PythonShape, SourceSet, UnknownSource,
    normalize_source,
)


## Resolve receiver and result ownership using SingleFileAnalyzer state.
class SingleFileReceiverResolutionMixin:
    ## --- Method resolution ---

    ## Resolve a method inherited from a statically known builtin base class.
    #
    #  Follows local base classes in declared MRO order.  A local override wins;
    #  an external or otherwise unknown base stops inference so a later builtin
    #  base cannot be claimed speculatively.
    #  @param class_name Local class whose bases should be inspected.
    #  @param method_name Method looked up on the instance.
    #  @param seen Local classes already visited during recursive lookup.
    #  @return Builtin type name, "local", or None when unresolved.
    def _inherited_builtin_method_owner(self, class_name, method_name,
                                        seen=None):
        if seen is None:
            seen = set()
        if class_name in seen:
            return None
        seen = set(seen)
        seen.add(class_name)

        for base in self.class_bases.get(class_name, []):
            if base in self.class_methods:
                if method_name in self.class_methods.get(base, []):
                    return "local"
                inherited = self._inherited_builtin_method_owner(
                    base, method_name, seen)
                if inherited is not None:
                    return inherited
                continue

            direct = normalize_source(self.symbols.direct.get(base))
            if direct == "local":
                return None

            imported = self.import_from_symbols.get(base, "")
            resolved_base = imported or base
            builtin_name = resolved_base.rsplit(".", 1)[-1]
            builtin_origin = (
                resolved_base == builtin_name
                or resolved_base.startswith("builtins."))
            if (builtin_origin
                    and method_name in _BUILTIN_CONTAINER_METHODS.get(
                        builtin_name, frozenset())):
                return builtin_name
            if builtin_name == "object" and builtin_origin:
                continue

            # An earlier unknown/external base may provide the descriptor.
            return None
        return None


    ## Resolve the owner of a comparison-result method call.
    #
    #  For (np.diag(W) == np.zeros(...)).any(), both sides of the
    #  comparison are numpy expressions, so the result is a boolean
    #  ndarray and .any() belongs to numpy.
    #
    #  Only returns an owner when ALL operands resolve to the same
    #  library AND the method is in _COMPARE_RESULT_METHODS for that
    #  library.  Returns None otherwise — no fallback to the first
    #  operand (which would overclaim ownership for mixed libraries).
    #  @param compare_node The ast.Compare node.
    #  @param method_name The method being called on the result.
    #  @return InstanceMethod or None.
    def _resolve_compare_result_top(self, compare_node, method_name):
        # Collect the top library of every operand.
        operands = [compare_node.left] + list(compare_node.comparators)
        tops = []
        for op in operands:
            base = self.get_base(op)
            if isinstance(base, str):
                top = self.symbols.get_top(base)
                if top and top not in ("local", "python", "unknown", ""):
                    tops.append(top)
                    continue
            # Could not resolve this operand — conservative bail-out.
            return None

        if not tops:
            return None

        first = tops[0]
        # All operands must have the same owner.
        if any(t != first for t in tops[1:]):
            return None

        # Only allow methods known to exist on compare-result objects.
        allowed = _COMPARE_RESULT_METHODS.get(first)
        if allowed is None or method_name not in allowed:
            return None

        return InstanceMethod(first, method_name)

    ## Flatten an attribute chain (e.g. a.b.c) into a list ["a", "b", "c"].
    #  @param node The starting Attribute node.
    #  @return List of name parts from root to leaf, or None.
    def _attribute_chain_list(self, node):
        parts = []
        remain = node
        while isinstance(remain, ast.Attribute):
            parts.append(remain.attr)
            remain = remain.value
        if isinstance(remain, ast.Name):
            parts.append(remain.id)
            return list(reversed(parts))
        return None

    ## Reconstruct a dotted attribute name from an AST node.
    #  @param node The Attribute or Name node.
    #  @return Dotted name string (e.g. "os.path.join"), or None.
    def _attribute_name(self, node):
        chain = self._attribute_chain_list(node)
        if chain:
            return ".".join(chain)
        return None

    ## Check whether an expression is rooted at an imported module symbol.
    #
    #  This is deliberately syntactic.  A variable whose value came from an
    #  external call is not treated as the module that produced that value.
    #  @param node Receiver expression below an Attribute node.
    #  @return True only for an import alias or import-from root.
    def _is_import_backed_receiver_expression(self, node):
        if isinstance(node, ast.Name):
            root = node.id
        elif isinstance(node, ast.Attribute):
            chain = self._attribute_chain_list(node)
            root = chain[0] if chain else None
        else:
            root = None
        if not root:
            return False
        if (root not in self.import_aliases
                and root not in self.import_from_symbols):
            return False
        top = self._receiver_top(root)
        return top not in (None, "", "local", "python", "unknown")

    ## Resolve an explicitly evidenced external receiver expression.
    #
    #  Accepted roots are import symbols and instance fields already bound to
    #  an external source. A local variable is intentionally excluded even
    #  when its current source came from an external call, because that call's
    #  return object has no generic static owner contract.
    #  @param node Receiver expression.
    #  @return External owner top or None.
    def _explicit_external_receiver_top(self, node):
        if self._is_import_backed_receiver_expression(node):
            if isinstance(node, ast.Name):
                root = node.id
            else:
                chain = self._attribute_chain_list(node)
                root = chain[0] if chain else None
            return self._receiver_top(root) if root else None

        if isinstance(node, ast.Attribute) and self._class_stack:
            chain = self._attribute_chain_list(node) or []
            if chain and chain[0] == "self":
                class_name = self._class_stack[-1]
                for end in range(len(chain), 1, -1):
                    field_name = ".".join(chain[:end])
                    source = normalize_source(self.instance_attrs.get(
                        (class_name, field_name)))
                    owner = self._structured_source_owner_top(source)
                    if owner not in (None, "", "local", "python", "unknown"):
                        return owner

        if isinstance(node, ast.Subscript):
            return self._explicit_external_receiver_top(node.value)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            receiver = node.func.value
            if self._is_import_backed_receiver_expression(receiver):
                return None
            return self._explicit_external_receiver_top(receiver)
        if isinstance(node, ast.Attribute):
            return self._explicit_external_receiver_top(node.value)
        return None

    ## Check whether an expression is rooted at a local instance field.
    #  @param node Receiver expression.
    #  @return True for self.field and its subscripted forms.
    def _is_instance_field_expression(self, node):
        if isinstance(node, ast.Attribute):
            chain = self._attribute_chain_list(node)
            return bool(chain and chain[0] == "self")
        if isinstance(node, ast.Subscript):
            return self._is_instance_field_expression(node.value)
        return False

    ## Find the root receiver of a call expression.
    #
    #  Unwinds chained calls and attributes to find the base object.
    #  @param receiver_node The receiver AST node.
    #  @return Base symbol name, or None.
    ## Resolve an Attribute receiver through scope binding.
    #
    #  When the root of the attribute chain (e.g. "v" in "v.armW.mean")
    #  has a scope binding with a library source, propagate it instead
    #  of returning the raw dotted name.
    #  @param receiver_node The Attribute AST node.
    #  @param receiver_name The full dotted name (e.g. "v.armW").
    #  @return Resolved source or the original receiver_name.
    def _resolve_attribute_receiver_chain(self, receiver_node, receiver_name):
        if receiver_name in self.symbols.direct:
            return receiver_name
        chain = self._attribute_chain_list(receiver_node)
        if chain:
            root_src = self._lookup_name_source(chain[0])
            if root_src and root_src != chain[0]:
                return root_src
        return receiver_name

    def _resolve_call_receiver(self, receiver_node):
        if isinstance(receiver_node, ast.Name):
            return self._lookup_name_source(receiver_node.id)
        if isinstance(receiver_node, ast.Attribute):
            receiver_name = self._attribute_name(receiver_node)
            if receiver_name is not None:
                return self._resolve_attribute_receiver_chain(
                    receiver_node, receiver_name)
            return self._resolve_call_receiver(receiver_node.value)
        if isinstance(receiver_node, ast.Call):
            inner_receiver = self.get_base(receiver_node, call_lookup=True)
            if inner_receiver is not None:
                return inner_receiver
            return self.get_base(receiver_node.func, call_lookup=False)
        if isinstance(receiver_node, ast.BinOp):
            left = self.get_base(receiver_node.left, call_lookup=True)
            if left is not None:
                return left
            return self.get_base(receiver_node.right, call_lookup=True)
        if isinstance(receiver_node, ast.Subscript):
            return self._resolve_call_receiver(receiver_node.value)
        return None

    ## --- Base extraction ---

    ## Extract the root/base name from an expression node.
    #
    #  For simple names returns the name. For attributes returns the chain root.
    #  For calls with call_lookup=True, resolves the call receiver.
    #  @param node The AST expression node.
    #  @param call_lookup If True, resolve call receivers instead of just func base.
    #  @return Root symbol name, or None.
    def get_base(self, node, call_lookup=False):
        if isinstance(node, ast.Name):
            return self._lookup_name_source(node.id)
        elif isinstance(node, ast.Attribute):
            chain = self._attribute_chain_list(node)
            if chain:
                name = '.'.join(chain)
                if name in self.symbols.direct:
                    return name
                if chain[0] == "self" and self._class_stack:
                    cn = self._class_stack[-1]
                    attr_source = self.instance_attrs.get((cn, name))
                    if attr_source is not None:
                        if isinstance(attr_source, str):
                            if attr_source in self.symbols.direct or '.' in attr_source:
                                return attr_source
                        else:
                            return attr_source
                root = chain[0]
                return self._lookup_name_source(root)
            return self.get_base(node.value, call_lookup=call_lookup)
        elif isinstance(node, ast.Call):
            if self._is_partial_call(node) and node.args:
                return self.get_base(node.args[0], call_lookup=call_lookup)
            if call_lookup:
                func = node.func
                if isinstance(func, ast.Attribute):
                    return self._resolve_call_receiver(func.value)
                if isinstance(func, ast.Call):
                    return self._resolve_call_receiver(func)
                if isinstance(func, ast.Name):
                    return self._lookup_name_source(func.id)
                return None
            return self.get_base(node.func, call_lookup=False)
        elif isinstance(node, ast.BinOp):
            left = self.get_base(node.left, call_lookup=call_lookup)
            if left is not None:
                return left
            return self.get_base(node.right, call_lookup=call_lookup)
        elif isinstance(node, ast.Lambda):
            return self.get_base(node.body, call_lookup=call_lookup)
        elif isinstance(node, ast.Subscript):
            return self.get_base(node.value, call_lookup=call_lookup)
        return None

    ## --- Visit handlers ---


    ## Resolve a receiver name to its top library using lexical scope.
    def _receiver_top(self, name):
        binding = self.current_scope().lookup(
            name, skip_parent_classes=True)
        if binding is not None:
            src = normalize_source(binding.source)
            if isinstance(src, str):
                if src in ("local", "python", "unknown", ""):
                    return src or None
                source_top = self.symbols.get_top(src)
                return source_top or src
            if isinstance(src, InstanceMethod):
                receiver = normalize_source(src.receiver)
                if isinstance(receiver, str):
                    receiver_top = self.symbols.get_top(receiver)
                    return receiver_top or receiver
                return None
            if isinstance(src, CallResult):
                result_owner = normalize_source(src.result_source)
                if isinstance(result_owner, str):
                    owner_top = self.symbols.get_top(result_owner)
                    return owner_top or result_owner
                if isinstance(result_owner, UnknownSource):
                    return "unknown"
                if not isinstance(src.callee, str):
                    return None
                callee_top = self.symbols.get_top(src.callee)
                root = src.callee.split(".", 1)[0]
                root_binding = self.current_scope().lookup(
                    root, skip_parent_classes=True)
                if ("." in src.callee and root_binding is not None
                        and root_binding.binding_kind == "import"
                        and isinstance(root_binding.source, str)):
                    callee_top = root_binding.source.split(".", 1)[0]
                if callee_top and callee_top not in ("local", name):
                    return callee_top
                # Follow return_sources through local functions.
                rs = self.return_sources.get(src.callee)
                if rs is not None:
                    rs = normalize_source(rs)
                    sources = rs.sources if isinstance(rs, SourceSet) else [rs]
                    for source in sources:
                        source = normalize_source(source)
                        if (isinstance(source, CallResult)
                                and isinstance(source.callee, str)):
                            callee_top = self.symbols.get_top(source.callee)
                            if (callee_top
                                    and callee_top not in ("local", name)):
                                return callee_top
                return callee_top
            # A lexical binding is authoritative. Do not consult a same-name
            # module binding when its structured source is unresolved here.
            return None
        top = self.symbols.get_top(name)
        return top

    ## Resolve the ownership top of an expression node.
    #  Recursively handles ast.Call arguments so that
    #  np.log(price.dropna()).diff() preserves the inner call's
    #  receiver owner (pandas).
    #  Respects conversion boundaries: data.to_numpy() returns
    #  numpy even though the receiver is pandas.
    def _expr_receiver_top(self, expr):
        if isinstance(expr, ast.Name):
            return self._receiver_top(expr.id)
        if isinstance(expr, ast.Constant):
            return "python"
        if isinstance(expr, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            return "python"
        if isinstance(expr, ast.UnaryOp):
            return self._expr_receiver_top(expr.operand)
        if isinstance(expr, ast.BinOp):
            left_top = self._expr_receiver_top(expr.left)
            right_top = self._expr_receiver_top(expr.right)
            if left_top == right_top:
                return left_top
            external = [
                top for top in (left_top, right_top)
                if top not in (None, "", "local", "python", "unknown")]
            other = [
                top for top in (left_top, right_top)
                if top not in external]
            if (len(set(external)) == 1
                    and all(top == "python" for top in other)):
                return external[0]
            return None
        if isinstance(expr, ast.Subscript):
            return self._expr_receiver_top(expr.value)
        if isinstance(expr, ast.Attribute):
            receiver = expr.value
            name = self._attribute_name(expr)
            if (name and name.startswith("self.")
                    and self._class_stack):
                field_source = normalize_source(self.instance_attrs.get(
                    (self._class_stack[-1], name)))
                field_top = self._structured_source_owner_top(field_source)
                if field_top not in (None, "", "local", "python", "unknown"):
                    return field_top
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top:
                    return _CONVERSION_ATTRIBUTE_TARGETS.get(
                        (receiver_top, expr.attr))
            return None
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute):
            receiver_top = self._expr_receiver_top(expr.func.value)
            if (receiver_top
                    and receiver_top not in (
                        "local", "python", "unknown", "")):
                # Check conversion boundary first:
                # data.to_numpy() return is numpy, not pandas.
                conv = _CONVERSION_METHOD_TARGETS.get(
                    (receiver_top, expr.func.attr))
                if conv:
                    return conv
                return receiver_top
        return None

    ## Identify one imported attribute path by its lexical root binding.
    #  @param node Attribute expression.
    #  @return Binding key and attribute path, or None for non-import roots.
    def _import_attribute_key(self, node):
        if not isinstance(node, ast.Attribute):
            return None
        chain = self._attribute_chain_list(node)
        if not chain:
            return None
        binding = self.current_scope().lookup(
            chain[0], skip_parent_classes=True)
        if binding is None or binding.binding_kind != "import":
            return None
        return (self._binding_key(binding), tuple(chain[1:]))

    ## Record runtime attributes of imported objects used via subscripting.
    #
    #  A subscript proves only that the attribute supports the subscription
    #  protocol. It does not prove that the attribute value is owned by the
    #  library that owns the outer object. Later method calls on the same
    #  attribute therefore remain unknown unless independent shape evidence
    #  exists.
    #  @param node Subscript expression.
    def visit_Subscript(self, node):
        key = self._import_attribute_key(node.value)
        if key is not None:
            self._subscripted_import_attribute_receivers.add(key)
        self.generic_visit(node)

    ## Check whether a return expression is fully bounded by project sources.
    #  @param source Structured return-expression source.
    #  @return True when exact call-edge substitution is safe.
    def _is_bounded_return_expression(self, source):
        source = normalize_source(source)
        if isinstance(source, (ParameterSource, InstanceAttribute,
                               PythonShape)):
            return True
        if isinstance(source, str):
            return source == "python"
        if isinstance(source, DerivedResult):
            return (
                source.kind == "expression"
                and bool(source.sources)
                and all(self._is_bounded_return_expression(item)
                        for item in source.sources)
            )
        if isinstance(source, CallResult):
            return (
                source.result_source is not None
                and self._is_bounded_return_expression(
                    source.result_source)
            )
        return False

    ## Check whether a structured source still depends on a parameter.
    #
    #  Parameter expressions must be resolved from project call edges.  A
    #  same-scope expression owner must not overwrite that richer evidence.
    #  @param source Source value to inspect.
    #  @return True when any nested source is parameter-backed.
    def _source_contains_parameter(self, source):
        source = normalize_source(source)
        if isinstance(source, ParameterSource):
            return True
        if isinstance(source, (DerivedResult, SourceSet)):
            return any(self._source_contains_parameter(item)
                       for item in source.sources)
        if isinstance(source, CallResult):
            return self._source_contains_parameter(source.result_source)
        if isinstance(source, InstanceMethod):
            return self._source_contains_parameter(source.receiver)
        return False

    ## Collect immediate ownership evidence from an operator expression.
    #
    #  The caller uses these candidates only to distinguish strict
    #  same-owner convergence from conflicting import-backed operands.
    #  @param expr BinOp or UnaryOp expression.
    #  @return List of operand owner strings.
    def _operator_operand_tops(self, expr):
        if isinstance(expr, ast.BinOp):
            return [
                self._expr_receiver_top(expr.left),
                self._expr_receiver_top(expr.right),
            ]
        if isinstance(expr, ast.UnaryOp):
            return [self._expr_receiver_top(expr.operand)]
        return []

    ## Resolve (top_library, function_name) for a function expression.
    #  Handles both bare names (cdist) and dotted names (np.log).
    def _resolve_func_top(self, func_node):
        if isinstance(func_node, ast.Name):
            name = func_node.id
            top = self._receiver_top(name)
            imported_name = self.import_from_symbols.get(name, "")
            func_name = (
                imported_name.rsplit(".", 1)[-1]
                if imported_name else name)
            if (top and top not in ("local", "python", "unknown", "")
                    and (top != name
                         or name in self.import_aliases
                         or name in self.import_from_symbols)):
                return (top, func_name)
        if isinstance(func_node, ast.Attribute):
            full_name = self._attribute_name(func_node)
            prefix = ""
            if full_name:
                imported_prefixes = sorted(
                    (
                        name for name in self.import_aliases
                        if (full_name == name
                            or full_name.startswith(name + "."))
                    ),
                    key=len,
                    reverse=True,
                )
                if imported_prefixes:
                    prefix = imported_prefixes[0]
                else:
                    prefix = full_name.split(".", 1)[0]
            prefix_top = self._receiver_top(prefix)
            if (prefix_top
                    and prefix_top not in ("local", "python", "unknown", "")
                    and (prefix_top != prefix
                         or prefix in self.import_aliases
                         or prefix in self.import_from_symbols)):
                return (prefix_top, func_node.attr)
        return (None, None)

    ## Resolve a verified owner for an item selected from a call result.
    #
    #  Direct import calls use _resolve_func_top().  Receiver calls additionally
    #  use _resolve_methods(), which can recover owners stored on instance
    #  attributes such as self.model = GPRegression(...).
    #  @param call_node The call whose result is indexed or destructured.
    #  @return Verified item owner string, or None.
    def _resolve_call_result_item_owner(self, call_node):
        func_top, func_name = self._resolve_func_top(call_node.func)
        owner = _match_result_item_owner(func_top, func_name)
        if owner is not None:
            return owner
        method_source = normalize_source(self._resolve_methods(call_node))
        if isinstance(method_source, InstanceMethod):
            receiver = normalize_source(method_source.receiver)
            if isinstance(receiver, str):
                receiver_top = self.symbols.get_top(receiver) or receiver
                if receiver_top not in (
                        None, "", "local", "python", "unknown"):
                    return _match_result_item_owner(
                        receiver_top, method_source.method)
        if (not isinstance(call_node.func, ast.Attribute)
                or not isinstance(call_node.func.value, ast.Attribute)
                or not self._class_stack):
            return None
        receiver_name = self._attribute_name(call_node.func.value)
        if not receiver_name or not receiver_name.startswith("self."):
            return None
        attr_source = normalize_source(self.instance_attrs.get(
            (self._class_stack[-1], receiver_name)))
        if isinstance(attr_source, CallResult):
            attr_source = normalize_source(
                attr_source.result_source or attr_source.callee)
        if not isinstance(attr_source, str):
            return None
        attr_top = self.symbols.get_top(attr_source) or attr_source
        if attr_top in (None, "", "local", "python", "unknown"):
            return None
        return _match_result_item_owner(attr_top, call_node.func.attr)

    ## Resolve the result owner of a protocol-dispatched NumPy ufunc.
    #
    #  Pandas and NumPy inputs retain their owner.  Python literals and
    #  containers produce NumPy results.  An unresolved or other import-backed
    #  receiver remains unknown because array protocols may override dispatch.
    #  @param call_node Ufunc call expression.
    #  @param func_top Resolved callable owner.
    #  @param func_name Resolved function name.
    #  @return Owner string, structured deferred source, UnknownSource, or
    #  None when not applicable.
    def _receiver_preserving_result_owner(self, call_node, func_top,
                                          func_name):
        if (func_top != "numpy"
                or func_name not in _RECEIVER_PRESERVE_UFUNCS
                or not call_node.args):
            return None
        arg_tops = []
        deferred_sources = []
        for argument in call_node.args:
            arg_top = self._expr_receiver_top(argument)
            if (_container_kind(argument) is not None
                    or isinstance(argument, ast.Constant)):
                arg_top = "python"
            if arg_top in (None, "", "local", "unknown"):
                dependency = self._parameter_dependency_source(
                    argument, expression_context=True)
                dependency = normalize_source(dependency)
                if dependency is None or isinstance(
                        dependency, UnknownSource):
                    return UnknownSource(
                        "receiver-preserving ufunc result")
                deferred_sources.append(dependency)
            else:
                deferred_sources.append(arg_top)
            arg_tops.append(arg_top)

        if any(top in (None, "", "local", "unknown")
               for top in arg_tops):
            return DerivedResult(
                "receiver_preserving_ufunc",
                tuple(deferred_sources),
                func_name,
            )

        external = set(top for top in arg_tops if top != "python")
        if not external:
            return "numpy"
        if len(external) == 1:
            owner = next(iter(external))
            if owner in ("pandas", "numpy"):
                return owner
        return UnknownSource("receiver-preserving ufunc result")

    ## Check whether a call expression is a known library-to-library conversion.
    #
    #  Unwraps trailing attribute chains (e.g. data.to_numpy().T) to find
    #  the inner conversion call, then looks up (source_library, method).
    #  @param value_node The RHS expression node.
    #  @return The conversion target library name, or None.
    def _resolve_conversion_target(self, value_node):
        # Unwrap trailing attribute chain: data.to_numpy().T → data.to_numpy()
        call_node = value_node
        while isinstance(call_node, ast.Attribute) and isinstance(call_node.value, (ast.Call, ast.Attribute)):
            call_node = call_node.value

        if isinstance(call_node, ast.Call) and isinstance(call_node.func, ast.Attribute):
            # Method call: data.to_numpy() → conversion if method in table.
            method = call_node.func.attr
            receiver = call_node.func.value
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top and receiver_top not in ("local", "python", "unknown", ""):
                    conv = _CONVERSION_METHOD_TARGETS.get((receiver_top, method))
                    if conv:
                        return conv
            # Not a known conversion method — fall through to check
            # function-call return types (e.g. np.log, cdist).

        if isinstance(call_node, ast.Attribute):
            # Bare attribute read: data.values → conversion if attr in table.
            # Bare method references (data.to_numpy without call) are NOT
            # conversions — saving a method object does not change the result type.
            attr_name = call_node.attr
            receiver = call_node.value
            if isinstance(receiver, ast.Name):
                receiver_top = self._receiver_top(receiver.id)
                if receiver_top and receiver_top not in ("local", "python", "unknown", ""):
                    return _CONVERSION_ATTRIBUTE_TARGETS.get((receiver_top, attr_name))
            return None

        # 1.0.5 P1: function-call return type.  cdist(...) → numpy,
        # receiver-preserving ufunc np.log(pd.Series) → pandas.
        if isinstance(call_node, ast.Call):
            func_top, func_name = self._resolve_func_top(call_node.func)
            if func_top and func_top not in ("local", "python", "unknown", ""):
                # Check explicit result-owner map (cdist → numpy).
                ret = _match_result_owner(func_top, func_name)
                if ret:
                    return ret
                preserved = self._receiver_preserving_result_owner(
                    call_node, func_top, func_name)
                if preserved is not None:
                    return preserved
        return None

    ## Resolve a class identity through already defined local return summaries.
    #  @param source Receiver value, not the name of the producing method.
    #  @param seen Local return-summary cycle guard.
    #  @return Local class name or None without uniform constructor evidence.
    def _returned_local_class_name(self, source, seen=None):
        source = normalize_source(source)
        seen = set(seen or ())
        if isinstance(source, SourceSet):
            names = [self._returned_local_class_name(item, seen)
                     for item in source.sources]
            return (names[0] if names and names[0] is not None
                    and all(name == names[0] for name in names) else None)
        if isinstance(source, CallResult) and isinstance(source.callee, str):
            callee = source.callee
            if callee in self.class_methods:
                return callee
            if callee not in seen:
                seen.add(callee)
                return self._returned_local_class_name(
                    self.return_sources.get(callee), seen)
        if isinstance(source, str) and source in self.class_methods:
            return source
        return None
