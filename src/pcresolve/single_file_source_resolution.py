## @package pcresolve.single_file_source_resolution
#  Expression-to-source tracing for the single-file ownership visitor.

import ast

from .builtin_ownership import _BUILTIN_CONTAINER_METHODS
from .ownership_contracts import (
    _is_verified_result_owner, _match_result_owner,
    _match_result_python_shape,
)
from .single_file_assignment import _builtin_value_source
from .single_file_call_collection import _is_unshadowed_builtin_call
from .sources import (
    ContainerItem, ContainerIter, DerivedResult, InstanceMethod, PythonShape,
    SuperMethod, CallResult, UnknownSource, SourceSet, normalize_source,
    make_source_set,
)


_BUILTIN_PYTHON_OWNED_RESULT = frozenset({
    "open", "super",
    "str", "int", "float", "bool", "list", "dict", "set", "tuple",
    "bytes", "bytearray", "complex", "frozenset", "object",
    "range", "slice", "memoryview",
    "staticmethod", "classmethod", "property",
    "enumerate", "filter", "map", "zip", "sorted",
    "len", "print", "exec",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "RuntimeError", "StopIteration", "OSError", "NotImplementedError",
    "AttributeError", "ImportError", "NameError", "SyntaxError",
    "ZeroDivisionError", "OverflowError", "EOFError", "IOError",
    "FileNotFoundError", "StopAsyncIteration",
})

_BUILTIN_ARBITRARY_RESULT = frozenset({"eval", "exec"})
_BUILTIN_ELEMENT_DERIVED = frozenset({"next", "min", "max"})
_BUILTIN_PROTOCOL_DERIVED = frozenset({"abs"})


## Resolve the element source carried by an iterable expression.
#  @param node Iterable AST expression.
#  @param trace_fn Callable to trace an AST expression.
#  @return Source value describing the iterable's possible elements.
def _iterable_element_source(node, trace_fn):
    if isinstance(node, ast.Name):
        traced = normalize_source(trace_fn(node))
        if isinstance(traced, CallResult):
            result_source = normalize_source(traced.result_source)
            if (isinstance(result_source, DerivedResult)
                    and result_source.kind == "iterator"
                    and result_source.sources):
                return result_source.sources[0]
        return ContainerIter(node.id)

    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        sources = [_builtin_value_source(elt, trace_fn) for elt in node.elts]
        if sources:
            return make_source_set(sources, origin="builtin_element")
        return UnknownSource("empty iterable")

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        if node.func.id in ("iter", "reversed") and node.args:
            return _iterable_element_source(node.args[0], trace_fn)
        if node.func.id == "enumerate" and node.args:
            return "python"

    traced = normalize_source(trace_fn(node))
    if isinstance(traced, CallResult):
        result_source = normalize_source(traced.result_source)
        if (isinstance(result_source, DerivedResult)
                and result_source.kind == "iterator"
                and result_source.sources):
            return result_source.sources[0]
    if traced is not None:
        return ContainerIter(traced)
    return UnknownSource("iterable element")


## Resolve element source for min/max/next arguments.
#  @param name Bare builtin name.
#  @param call_node The ast.Call node.
#  @param trace_fn Callable to trace an AST expression.
#  @return Derived element result or an unknown source.
def _element_source(name, call_node, trace_fn):
    sources = []
    if name in ("min", "max") and len(call_node.args) > 1:
        sources.extend(_builtin_value_source(arg, trace_fn)
                       for arg in call_node.args)
    elif call_node.args:
        sources.append(_iterable_element_source(call_node.args[0], trace_fn))

    if name in ("min", "max"):
        for keyword in call_node.keywords:
            if keyword.arg == "default":
                sources.append(_builtin_value_source(keyword.value, trace_fn))
    elif name == "next" and len(call_node.args) > 1:
        sources.append(_builtin_value_source(call_node.args[1], trace_fn))

    if not sources:
        return UnknownSource("element")
    return DerivedResult(
        "element", (make_source_set(sources, origin="builtin_element"),))


## Return the result source for a known builtin callable.
#  @param name Bare builtin name.
#  @param call_node The ast.Call node.
#  @param trace_fn Callable to trace an AST expression to its source.
#  @return Known result source or None.
def _resolve_builtin_result(name, call_node, trace_fn):
    if not isinstance(name, str):
        return None
    if name in _BUILTIN_PYTHON_OWNED_RESULT:
        return "python"
    if name in _BUILTIN_ARBITRARY_RESULT:
        return UnknownSource(name)
    if name in _BUILTIN_ELEMENT_DERIVED and call_node and call_node.args:
        return _element_source(name, call_node, trace_fn)
    if name == "type" and call_node and call_node.args:
        arg_node = call_node.args[0]
        arg_source = trace_fn(arg_node)
        if isinstance(arg_node, ast.Call):
            callee_id = None
            if isinstance(arg_node.func, ast.Name):
                callee_id = arg_node.func.id
            elif isinstance(arg_node.func, ast.Attribute):
                callee_id = trace_fn(arg_node)
            if callee_id is not None:
                callee_norm = normalize_source(callee_id)
                if (isinstance(callee_norm, CallResult)
                        and isinstance(callee_norm.callee, str)):
                    callee_id = callee_norm.callee
                return DerivedResult("type_of", (callee_id,))
        if arg_source is not None:
            return DerivedResult("type_of", (arg_source,))
        return UnknownSource("type")
    if name == "__import__" and call_node and call_node.args:
        first_arg = call_node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            return first_arg.value.split(".")[0]
        return UnknownSource("__import__")
    if name in ("iter", "reversed") and call_node and call_node.args:
        element = _iterable_element_source(call_node.args[0], trace_fn)
        return DerivedResult("iterator", (element,))
    if name in _BUILTIN_PROTOCOL_DERIVED:
        return UnknownSource(name)
    return None


## Check whether every possible return source is Python-owned.
#  @param source Return source or SourceSet.
#  @return True when all possible sources are exactly Python-owned.
def _is_uniform_python_result(source):
    source = normalize_source(source)
    if source == "python" or isinstance(source, PythonShape):
        return True
    if isinstance(source, SourceSet) and source.sources:
        return all(_is_uniform_python_result(item) for item in source.sources)
    return False


## Check whether any possible return source is Python-owned.
#  @param source Return source or SourceSet.
#  @return True when at least one branch is Python-owned.
def _has_python_result(source):
    source = normalize_source(source)
    if source == "python" or isinstance(source, PythonShape):
        return True
    if isinstance(source, SourceSet):
        return any(_has_python_result(item) for item in source.sources)
    return False


## Return one concrete Python shape when every return branch agrees.
#  @param source Return source or SourceSet.
#  @return Common PythonShape, otherwise None.
def _uniform_python_shape(source):
    source = normalize_source(source)
    if isinstance(source, PythonShape):
        return source
    if isinstance(source, CallResult):
        result_source = normalize_source(source.result_source)
        return result_source if isinstance(result_source, PythonShape) else None
    if isinstance(source, SourceSet) and source.sources:
        shapes = [_uniform_python_shape(item) for item in source.sources]
        if (all(shape is not None for shape in shapes)
                and all(shape == shapes[0] for shape in shapes[1:])):
            return shapes[0]
    return None


## Expression source resolver mixed into SingleFileAnalyzer.
class SingleFileSourceResolutionMixin:
    ## Trace an AST expression to its symbol or structured source.
    #  @param node AST expression.
    #  @return Source value or None.
    def trace_source(self, node):
        if isinstance(node, ast.Name):
            return self._lookup_name_source(node.id)
        if isinstance(node, ast.Call):
            return self._trace_call_source(node)
        if isinstance(node, ast.Attribute):
            name = self._attribute_name(node)
            if name and name in self.symbols.direct:
                return name
            return self.get_base(node)
        if isinstance(node, ast.Lambda):
            return self._trace_lambda_source(node)
        if isinstance(node, ast.Subscript):
            return self._trace_subscript_source(node)
        if isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
            return self._trace_literal_container_source(node)
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            return UnknownSource("yield expression result")
        return None

    ## Trace one call expression after special dynamic forms are considered.
    #  @param node Call AST node.
    #  @return Source value or None.
    def _trace_call_source(self, node):
        getattr_src = self._resolve_getattr_trace(node)
        selected = self._finite_eval_names(node)
        if selected is not None:
            return selected
        if getattr_src:
            return getattr_src
        import_mod = self._resolve_import_module_trace(node)
        if import_mod:
            return import_mod
        if self._is_partial_call(node) and node.args:
            return self.get_base(node.args[0])
        method = self._resolve_methods(node)
        if method:
            return self._trace_method_call_source(node, method)
        resolved, source = self._trace_chained_call_source(node)
        if resolved:
            return source
        return self._trace_regular_call_source(node)

    ## Convert a resolved method target into the call expression's value source.
    #  @param node Call AST node.
    #  @param method Resolved method source.
    #  @return Method call value source.
    def _trace_method_call_source(self, node, method):
        receiver_kind = self._call_receiver_container_kind(node)
        if (receiver_kind is not None
                and isinstance(method, InstanceMethod)
                and method.method in _BUILTIN_CONTAINER_METHODS.get(
                    receiver_kind, frozenset())):
            return CallResult(
                method, display_name=ast.unparse(node.func),
                call_lineno=node.lineno, call_col_offset=node.col_offset,
                result_source=self._builtin_method_result_source(
                    node, receiver_kind, method.method))
        if isinstance(method, InstanceMethod) and method.receiver == "python":
            return CallResult(
                method, display_name=ast.unparse(node.func),
                call_lineno=node.lineno, call_col_offset=node.col_offset,
                result_source="python")
        if (isinstance(method, InstanceMethod)
                and isinstance(method.method, str)
                and isinstance(method.receiver, str)):
            class_name = self._local_method_receiver_class(method.receiver)
            if class_name is not None:
                return CallResult(
                    class_name + "." + method.method,
                    display_name=ast.unparse(node.func),
                    call_lineno=node.lineno,
                    call_col_offset=node.col_offset)
        if isinstance(method, SuperMethod):
            return CallResult(
                method, display_name="super().%s" % method.method,
                call_lineno=node.lineno, call_col_offset=node.col_offset,
                result_source=UnknownSource("super()"))
        return method

    ## Resolve the local class identity carried by a method receiver.
    #  @param receiver Receiver source string.
    #  @return Local class name or None.
    def _local_method_receiver_class(self, receiver):
        if receiver in self.class_methods:
            return receiver
        binding = self.current_scope().lookup(receiver)
        if binding is not None:
            source = normalize_source(binding.source)
            if (isinstance(source, CallResult)
                    and isinstance(source.callee, str)
                    and source.callee in self.class_methods):
                return source.callee
        return None

    ## Resolve an outer chained call from the inner call's result evidence.
    #  @param node Outer Call AST node.
    #  @return Pair of handled flag and source value.
    def _trace_chained_call_source(self, node):
        if not (isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Call)):
            return False, None
        inner_source = self.trace_source(node.func.value)
        if isinstance(inner_source, str):
            result = self.return_sources.get(inner_source)
            if result is not None:
                result = normalize_source(result)
                if isinstance(result, SourceSet):
                    inner_source = result
                else:
                    return True, result
        if isinstance(inner_source, CallResult):
            if inner_source.result_source is not None:
                result_owner = inner_source.result_source
                if isinstance(result_owner, str):
                    mapped_owner = _match_result_owner(
                        result_owner, node.func.attr)
                    if mapped_owner is not None:
                        mapped_shape = _match_result_python_shape(
                            result_owner, node.func.attr)
                        return True, CallResult(
                            InstanceMethod(result_owner, node.func.attr),
                            display_name=ast.unparse(node.func),
                            call_lineno=node.lineno,
                            call_col_offset=node.col_offset,
                            result_source=(mapped_shape or mapped_owner))
                return True, result_owner
            result = self.return_sources.get(inner_source.callee)
            if result is not None:
                result = normalize_source(result)
                if isinstance(result, SourceSet):
                    inner_source = result
                else:
                    return True, result
        if isinstance(inner_source, SourceSet):
            return True, inner_source
        if inner_source:
            return True, inner_source
        return False, None

    ## Trace an ordinary call into a CallResult after callee lookup.
    #  @param node Call AST node.
    #  @return CallResult, fallback source, or None.
    def _trace_regular_call_source(self, node):
        if isinstance(node.func, ast.Name):
            binding = self.current_scope().lookup(
                node.func.id, skip_parent_classes=True)
            if binding is not None and binding.callable_key:
                call_key = binding.callable_key
            elif (node.func.id in self.defined_functions
                  or node.func.id in self.class_methods):
                call_key = node.func.id
            else:
                call_key = self.get_base(node, call_lookup=True)
        else:
            call_key = self.get_base(node, call_lookup=True)
        method_source = normalize_source(self._resolve_methods(node))
        if (isinstance(method_source, InstanceMethod)
                and isinstance(method_source.receiver, str)
                and _is_verified_result_owner(method_source.receiver)):
            call_key = method_source.receiver
        if not call_key:
            return self.get_base(node.func)
        if isinstance(call_key, CallResult):
            return call_key
        if (isinstance(call_key, str) and call_key.startswith("self.")
                and self._class_stack):
            class_name = self._class_stack[-1]
            attr_source = self.instance_attrs.get((class_name, call_key))
            if (isinstance(attr_source, CallResult)
                    and isinstance(attr_source.callee, str)):
                call_key = attr_source.callee
        if (isinstance(call_key, InstanceMethod)
                and isinstance(call_key.receiver, str)):
            call_key = call_key.receiver
        display = ""
        try:
            display = ast.unparse(node.func)
        except Exception:
            pass
        if isinstance(call_key, str) and '.' not in display:
            display = ""
        result_source = self._regular_call_result_source(node, call_key)
        return CallResult(
            call_key, display_name=display, call_lineno=node.lineno,
            call_col_offset=node.col_offset, result_source=result_source)

    ## Determine the result-object source for an ordinary resolved call.
    #  @param node Call AST node.
    #  @param call_key Resolved callee source.
    #  @return Result source or None.
    def _regular_call_result_source(self, node, call_key):
        if not isinstance(call_key, str):
            return None
        result_source = None
        local_returns = self.return_sources.get(call_key)
        local_shape = _uniform_python_shape(local_returns)
        if local_shape is not None:
            result_source = local_shape
        elif _is_uniform_python_result(local_returns):
            result_source = "python"
        elif _has_python_result(local_returns):
            result_source = UnknownSource("mixed local return")
        func_top, func_name = self._resolve_func_top(node.func)
        mapped_owner = _match_result_owner(func_top, func_name)
        if mapped_owner is not None:
            result_source = (
                _match_result_python_shape(func_top, func_name)
                or mapped_owner)
        else:
            preserved = self._receiver_preserving_result_owner(
                node, func_top, func_name)
            if preserved is not None:
                result_source = preserved
        if _is_unshadowed_builtin_call(self, node):
            result_source = _resolve_builtin_result(
                call_key, node, self.trace_source)
        return result_source

    ## Trace a lambda from its body without treating parameters as owners.
    #  @param node Lambda AST node.
    #  @return Body source or local.
    def _trace_lambda_source(self, node):
        body_base = self.get_base(node.body)
        if isinstance(body_base, str):
            param_names = {arg.arg for arg in node.args.args}
            if node.args.vararg:
                param_names.add(node.args.vararg.arg)
            if node.args.kwarg:
                param_names.add(node.args.kwarg.arg)
            if body_base in param_names:
                return "local"
        return body_base

    ## Trace an indexed expression through exact and homogeneous item facts.
    #  @param node Subscript AST node.
    #  @return Item source or container source.
    def _trace_subscript_source(self, node):
        if isinstance(node.value, ast.Call):
            item_owner = self._resolve_call_result_item_owner(node.value)
            if item_owner is not None:
                return item_owner
        container_name = self.trace_source(node.value)
        key_index = self._get_slice(node.slice)
        if container_name is not None and key_index is not None:
            lookup_name = (node.value.id if isinstance(node.value, ast.Name)
                           else container_name)
            key_value = self._container_index(lookup_name, key_index)
            lookup_key = (lookup_name, key_value)
            if lookup_key in self.container_items:
                return self.container_items[lookup_key]
            return ContainerItem(lookup_name, key_index)
        resolved_key = None
        if isinstance(node.value, ast.Name):
            var_name = node.value.id
            if isinstance(node.slice, ast.Name):
                resolved_key = self._literal_values.get(node.slice.id)
            if resolved_key is not None:
                lookup = self.container_items.get((var_name, resolved_key))
                if lookup is not None:
                    return lookup
            homogeneous = self.homogeneous_container_value_sources.get(var_name)
            if homogeneous is not None:
                return homogeneous
        if container_name is not None and isinstance(node.value, ast.Name):
            item_sources = [
                source for (name, _), source in self.container_items.items()
                if name == node.value.id]
            if item_sources:
                return make_source_set(item_sources, origin="dict_lookup")
        return container_name

    ## Trace a literal container only when every element has one common base.
    #  @param node Dict, list, tuple, or set AST node.
    #  @return Common base source or None.
    def _trace_literal_container_source(self, node):
        value_nodes = node.values if isinstance(node, ast.Dict) else node.elts
        bases = set()
        for value in value_nodes:
            base = self.get_base(value)
            if base:
                bases.add(base)
        return next(iter(bases)) if len(bases) == 1 else None

    ## Extract a string literal from an AST node.
    #  @param node AST node.
    #  @return String value or None.
    def _literal_str(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    ## Check whether a call is functools.partial-compatible syntax.
    #  @param node Call AST node.
    #  @return True for partial calls.
    def _is_partial_call(self, node):
        if not isinstance(node, ast.Call):
            return False
        func = node.func
        return ((isinstance(func, ast.Name) and func.id == 'partial')
                or (isinstance(func, ast.Attribute) and func.attr == 'partial'))

    ## Check whether a call is getattr-compatible syntax.
    #  @param node Call AST node.
    #  @return True for getattr calls with a name argument.
    def _is_getattr_call(self, node):
        if not isinstance(node, ast.Call) or len(node.args) < 2:
            return False
        func = node.func
        return ((isinstance(func, ast.Name) and func.id == "getattr")
                or (isinstance(func, ast.Attribute) and func.attr == "getattr"))

    ## Resolve getattr(obj, literal_name) to the object's source.
    #  @param node Call AST node.
    #  @return Object source or None.
    def _resolve_getattr_trace(self, node):
        if not self._is_getattr_call(node):
            return None
        if self._literal_str(node.args[1]) is None:
            return None
        return self.trace_source(node.args[0])

    ## Check whether a symbol ultimately originates from importlib.
    #  @param symbol Symbol to inspect.
    #  @return True for an importlib source.
    def _is_importlib_module(self, symbol):
        if not isinstance(symbol, str):
            return False
        return symbol == "importlib" or self.symbols.get_top(symbol) == "importlib"

    ## Check whether a call is importlib.import_module().
    #  @param node Call AST node.
    #  @return True for a proven import_module call.
    def _is_import_module_call(self, node):
        if not isinstance(node, ast.Call) or not node.args:
            return False
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "import_module":
            root = self.get_base(func.value)
            return bool(root and self._is_importlib_module(root))
        if isinstance(func, ast.Name) and func.id == "import_module":
            return (self.import_from_symbols.get("import_module") or "").startswith(
                "importlib")
        return False

    ## Resolve importlib.import_module(literal) to the module name.
    #  @param node Call AST node.
    #  @return Module name or None.
    def _resolve_import_module_trace(self, node):
        if not self._is_import_module_call(node):
            return None
        return self._literal_str(node.args[0])

    ## Extract a constant or negated constant from a slice node.
    #  @param slice_node Slice AST node.
    #  @return Constant value or None.
    def _get_slice(self, slice_node):
        if isinstance(slice_node, ast.Constant):
            return slice_node.value
        if (isinstance(slice_node, ast.UnaryOp)
                and isinstance(slice_node.op, ast.USub)
                and isinstance(slice_node.operand, ast.Constant)):
            return -slice_node.operand.value
        return None

    ## Normalize a negative container index when length is known.
    #  @param container_name Container binding name.
    #  @param idx Raw index.
    #  @return Adjusted index.
    def _container_index(self, container_name, idx):
        if not isinstance(idx, int) or idx >= 0:
            return idx
        length = self.container_lengths.get(container_name)
        return idx + length if length else idx
