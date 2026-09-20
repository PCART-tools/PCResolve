## @package pcresolve.single_file_call_collection
#  Collect call-edge and public API-call facts during single-file analysis.
#
#  The mixin operates on SingleFileAnalyzer visitor state so call ordering,
#  lexical bindings, and exact source positions remain snapshot-consistent.

import ast

from .builtin_ownership import _has_builtin_shape_method, _is_builtin
from .call_graph import CallEdge
from .program_facts import SourceSpan
from .scope import SCOPE_CLASS, SCOPE_FUNCTION, SCOPE_MODULE
from .sources import (
    CallResult, ContainerItem, ContainerIter, InstanceMethod, PythonShape,
    SourceSet, SuperMethod, UnknownSource, is_structured_source,
    normalize_source, source_display,
)


## Check whether a builtin name is not shadowed by a local definition.
#
#  @param self SingleFileAnalyzer instance.
#  @param node The ast.Call node.
#  @return True if the call is to an unshadowed builtin.
def _is_unshadowed_builtin_call(tracer, node):
    if not isinstance(node, ast.Call):
        return False
    if not isinstance(node.func, ast.Name):
        return False
    name = node.func.id
    if not _is_builtin(name):
        return False
    if name in tracer.defined_functions:
        return False
    if name in tracer.import_from_symbols:
        return False
    if name in tracer.local:
        return False
    # Check lexical scope binding for shadowing.
    binding = tracer.current_scope().lookup(
        name, skip_parent_classes=True)
    if binding is not None:
        return False
    return True


## Collect API call and call-edge facts using SingleFileAnalyzer state.
class SingleFileCallCollectionMixin:
    ## Record a single API call with its resolved top-level origin.
    #  @param node The Call AST node.
    def _one_api_call(self, node):
        if id(node) in self._seen_api_call_ids:
            return
        self._seen_api_call_ids.add(id(node))
        api_string = self.get_call(node)
        func_name, parameters = self._get_call_parts(node)
        base = self._resolve_call_base_for_api(node)
        if not base:
            return
        self._record_call_edge(node, base, func_name)
        direct_name = node.func.id if isinstance(node.func, ast.Name) else None
        location = self._call_location(node, func_name, parameters)
        self._snapshot_super_base_path(node, base, location)
        self._snapshot_call_assignment(func_name, location)
        if direct_name and _is_unshadowed_builtin_call(self, node):
            self._append_api_call(
                api_string, "python", ["python"], direct_name,
                direct_name, func_name, parameters, location)
            return
        receiver_kind = self._call_receiver_container_kind(node)
        method_name = (
            node.func.attr if isinstance(node.func, ast.Attribute) else "")
        if (receiver_kind is not None
                and _has_builtin_shape_method(receiver_kind, method_name)):
            location["receiver_container_kind"] = receiver_kind
            self._append_api_call(
                api_string, "python", ["python"], base,
                direct_name, func_name, parameters, location)
            return
        if isinstance(base, UnknownSource):
            self._append_api_call(
                api_string, "unknown", ["unknown"], base,
                direct_name, func_name, parameters, location)
            return
        if isinstance(base, CallResult):
            top, chain = self._call_result_record_source(base)
            self._append_api_call(
                api_string, top, chain, base, direct_name,
                func_name, parameters, location)
            return
        if self._is_structured_call_base(base):
            display, chain = self._structured_call_record_source(
                node, base, location)
            self._append_api_call(
                api_string, display, chain, base, direct_name,
                func_name, parameters, location)
            return
        if base == "local":
            self._append_api_call(
                api_string, "local", ["local"], "local",
                direct_name, func_name, parameters, location)
            return
        top = self.symbols.get_top(base)
        if top:
            self._append_api_call(
                api_string, top, self.symbols.get_chain(base), base,
                direct_name, func_name, parameters, location)

    ## Record the internal call edge before public call classification.
    def _record_call_edge(self, node, base, func_name):
        if not self._caller_stack:
            return
        (arg_sources, protocol_sources, iterable_sources,
         star_args, star_kwargs) = self._call_argument_sources(node)
        callback_args, callback_bindings = self._call_callback_sources(node)
        edge = CallEdge(
            caller=self._caller_stack[-1],
            callee=base,
            callee_name=func_name or "",
            callee_source=self._call_edge_callee_source(node.func),
            receiver_source=self._call_receiver_source(node),
            arg_sources=arg_sources,
            star_arg_sources=star_args,
            star_kwarg_sources=star_kwargs,
            callback_args=callback_args,
            callback_bindings=callback_bindings,
            protocol_arg_sources=protocol_sources,
            iterable_arg_sources=iterable_sources,
            assigned_to=self._pending_call_targets_by_node.pop(id(node), []),
            call_lineno=node.lineno,
            call_col_offset=node.col_offset,
            source_span=SourceSpan.from_ast(
                getattr(self, "_file_path", ""), node),
        )
        self.module_cg.edges.append(edge)
        mapping_value = self._mapping_facts.value(node.func)
        if mapping_value is not None and mapping_value.selected:
            self._mapping_edges.append((edge, mapping_value))

    ## Resolve the receiver source stored on a call edge.
    def _call_receiver_source(self, node):
        if not isinstance(node.func, ast.Attribute):
            return None
        receiver = node.func.value
        if (isinstance(receiver, ast.Name)
                and receiver.id in ("self", "cls")):
            return self.get_base(receiver)
        return self._call_edge_argument_source(receiver)

    ## Collect ordinary, protocol, iterable, and starred argument sources.
    def _call_argument_sources(self, node):
        ordinary = {"pos": {}, "kw": {}}
        protocol = {"pos": {}, "kw": {}}
        iterable = {"pos": {}, "kw": {}}
        star_args = {}
        positional_index = 0
        for argument in node.args:
            if isinstance(argument, ast.Starred):
                source = self._call_edge_argument_source(argument.value)
                if source is not None:
                    star_args[positional_index] = source
                positional_index = None
                continue
            self._record_positional_argument_sources(
                argument, positional_index, ordinary, protocol, iterable)
            if positional_index is not None:
                positional_index += 1
        star_kwargs = []
        for keyword in getattr(node, "keywords", []) or []:
            if keyword.arg is None:
                source = self._call_edge_argument_source(keyword.value)
                if source is not None:
                    star_kwargs.append(source)
                continue
            self._record_keyword_argument_sources(
                keyword, ordinary, protocol, iterable)
        return ordinary, protocol, iterable, star_args, star_kwargs

    ## Record the three source views for one positional argument.
    def _record_positional_argument_sources(
            self, argument, index, ordinary, protocol, iterable):
        if index is None:
            self._call_edge_argument_source(argument)
            self._call_edge_protocol_source(argument)
            self._call_edge_iterable_source(argument)
            return
        source = self._call_edge_argument_source(argument)
        if source is not None:
            ordinary["pos"][index] = source
        protocol_source = self._call_edge_protocol_source(argument)
        if protocol_source is not None:
            protocol["pos"][index] = protocol_source
        iterable_source = self._call_edge_iterable_source(argument)
        if iterable_source is not None:
            iterable["pos"][index] = iterable_source

    ## Record the three source views for one named keyword argument.
    def _record_keyword_argument_sources(
            self, keyword, ordinary, protocol, iterable):
        source = self._call_edge_argument_source(keyword.value)
        if source is not None:
            ordinary["kw"][keyword.arg] = source
        protocol_source = self._call_edge_protocol_source(keyword.value)
        if protocol_source is not None:
            protocol["kw"][keyword.arg] = protocol_source
        iterable_source = self._call_edge_iterable_source(keyword.value)
        if iterable_source is not None:
            iterable["kw"][keyword.arg] = iterable_source

    ## Collect callback positions and multiprocessing target/args bindings.
    def _call_callback_sources(self, node):
        callback_args = {}
        for index, argument in enumerate(node.args):
            callback_name = self._call_edge_callback_name(argument)
            if callback_name:
                callback_args[index] = callback_name
        keywords = getattr(node, "keywords", []) or []
        targets = {
            keyword.value.id for keyword in keywords
            if (keyword.arg == "target"
                and isinstance(keyword.value, ast.Name))
        }
        args_keyword = next(
            (keyword.value for keyword in keywords
             if keyword.arg == "args"), None)
        callback_source = self._call_edge_tuple_source(args_keyword)
        bindings = []
        if callback_source is not None:
            bindings = [
                {"callback": target, "args": callback_source}
                for target in sorted(targets)
            ]
        return callback_args, bindings

    ## Build stable source-position and lexical-scope call metadata.
    def _call_location(self, node, func_name, parameters):
        scope = self.current_scope()
        return {
            "func_name": func_name,
            "parameters": parameters,
            "lineno": node.lineno,
            "col_offset": node.col_offset,
            "end_lineno": getattr(node, "end_lineno", 0) or 0,
            "end_col_offset": getattr(node, "end_col_offset", 0) or 0,
            "scope_name": "" if scope.kind == SCOPE_MODULE else scope.name,
        }

    ## Snapshot a zero-argument super() receiver's class import path.
    def _snapshot_super_base_path(self, node, base, location):
        if not isinstance(normalize_source(base), SuperMethod):
            return
        location["super_base_path"] = None
        receiver = (
            node.func.value if isinstance(node.func, ast.Attribute) else None)
        scope = self.current_scope()
        if (not isinstance(receiver, ast.Call)
                or not isinstance(receiver.func, ast.Name)
                or receiver.func.id != "super"
                or receiver.args or receiver.keywords
                or not _is_unshadowed_builtin_call(self, receiver)
                or scope.kind != SCOPE_FUNCTION
                or scope.parent is None
                or scope.parent.kind != SCOPE_CLASS
                or not self._super_base_path_stack):
            return
        base_path, decorator_module = self._super_base_path_stack[-1]
        location["super_base_path"] = base_path
        location["super_decorator_module"] = decorator_module

    ## Snapshot flow-sensitive dotted-call assignment and import evidence.
    def _snapshot_call_assignment(self, func_name, location):
        if not func_name or "." not in func_name:
            return
        first = func_name.split(".")[0]
        location["call_assign_func"] = self.call_assign_funcs.get(first)
        binding = self.current_scope().lookup(
            first, skip_parent_classes=True)
        if (binding is not None
                and binding.binding_kind == "import"
                and binding.scope_kind != SCOPE_MODULE):
            location["call_import_source"] = (
                self._import_binding_sources.get(self._binding_key(binding))
                or binding.source)

    ## Resolve a CallResult's provisional single-file owner and chain.
    def _call_result_record_source(self, base):
        callee = base.callee
        explicit = base.result_source
        if explicit is not None:
            if isinstance(explicit, UnknownSource):
                top = "unknown"
            elif isinstance(explicit, PythonShape) or explicit == "python":
                top = "python"
            elif is_structured_source(explicit):
                top = source_display(base)
            else:
                top = str(explicit)
            return top, [source_display(base)]
        if not isinstance(callee, str):
            return source_display(base), [source_display(base)]
        returned = self.return_sources.get(callee)
        if returned is not None:
            resolved = normalize_source(returned)
            if (isinstance(resolved, CallResult)
                    and isinstance(resolved.callee, str)):
                callee = resolved.callee
            elif isinstance(resolved, SourceSet):
                top = source_display(base)
                return top, [top]
        top = self.symbols.get_top(callee) or source_display(base)
        return top, [source_display(base)]

    ## Return whether a call base requires deferred structured resolution.
    def _is_structured_call_base(self, base):
        return (isinstance(base, tuple)
                or isinstance(base, (
                    ContainerItem, ContainerIter, InstanceMethod,
                    SuperMethod, SourceSet)))

    ## Resolve a structured base's provisional owner and chain.
    def _structured_call_record_source(self, node, base, location):
        if (isinstance(base, InstanceMethod)
                and isinstance(base.receiver, str)
                and base.receiver == "__unresolved_compare__"):
            return "unknown", ["unknown"]
        display = source_display(base)
        if isinstance(base, InstanceMethod) and isinstance(base.receiver, str):
            display = self._instance_method_record_source(
                node, base, display, location)
        return display, [display] if display else []

    ## Apply builtin-container and local-receiver evidence at a call site.
    def _instance_method_record_source(self, node, base, display, location):
        receiver_top = self.symbols.get_top(base.receiver)
        receiver_is_local = receiver_top == "local"
        if not receiver_is_local:
            binding = self.current_scope().lookup(base.receiver)
            receiver_is_local = (
                binding is not None and binding.source == "local")
        kind = self._call_receiver_container_kind(node)
        if kind is not None and _has_builtin_shape_method(kind, base.method):
            location["receiver_container_kind"] = kind
            return "python"
        if receiver_is_local and not base.parameter_scope:
            return "local"
        return display

    ## Append one public call record and its structured call-site snapshot.
    def _append_api_call(
            self, api_string, top, chain, base, direct_name,
            func_name, parameters, location):
        record = {
            "api": api_string,
            "top": top,
            "chain": chain,
            "base": base,
            "direct_name_callee": direct_name,
        }
        record.update(location)
        self.api_calls.append(record)
        self._collect_call_site(
            api_string, func_name, parameters, base, location)
