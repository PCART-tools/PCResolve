## @package pcresolve.single_file_call_collection
#  Collect call-edge and public API-call facts during single-file analysis.
#
#  The mixin operates on SingleFileAnalyzer visitor state so call ordering,
#  lexical bindings, and exact source positions remain snapshot-consistent.

import ast
from dataclasses import replace

from .builtin_ownership import (
    _builtin_shape_type, _has_builtin_shape_method,
)
from .call_graph import CallEdge
from .ir import CallSite, SymbolRef
from .ownership_contracts import (
    _CALLBACK_PARAMETER_OWNER_CONTRACTS, _match_result_owner,
)
from .program_facts import SourceSpan
from .scope import (
    SCOPE_CLASS, SCOPE_COMPREHENSION, SCOPE_FUNCTION, SCOPE_MODULE,
)
from .single_file_assignment import _builtin_value_source
from .single_file_builtins import _is_unshadowed_builtin_call
from .single_file_source_resolution import (
    _BUILTIN_PYTHON_OWNED_RESULT, _iterable_element_source,
)
from .sources import (
    CallResult, ContainerItem, ContainerIter, InstanceMethod,
    ParameterSource, PythonShape, SourceSet, SuperMethod, TupleSource,
    UnknownSource, is_structured_source, make_source_set, normalize_source,
    source_display,
)

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
    ## Preserve a lexical local callable's identity on a call edge.
    #
    #  Nested functions and lambdas need their qualified binding key so
    #  call contexts cannot merge unrelated same-named local definitions.
    #  @param node Call target expression.
    #  @return Local callable key or the ordinary traced source.
    def _call_edge_callee_source(self, node):
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if (binding is not None and binding.callable_key
                    and binding.callable_key != node.id):
                return binding.callable_key
        return self.trace_source(node)
    ## Preserve a direct import-from callable for argument-flow evidence.
    #
    #  This metadata is intentionally separate from the ordinary symbol
    #  binding so public provenance and legacy call classification keep their
    #  established representation.
    #
    #  @param node Candidate call expression.
    #  @return Qualified CallResult or None.
    def _imported_call_result_source(self, node):
        if (not isinstance(node, ast.Call)
                or not isinstance(node.func, ast.Name)):
            return None
        qualified = self.import_from_symbols.get(node.func.id)
        if not qualified:
            return None
        traced = normalize_source(self.trace_source(node))
        return CallResult(
            qualified,
            display_name=node.func.id,
            call_lineno=node.lineno,
            call_col_offset=node.col_offset,
            result_source=(traced.result_source
                           if isinstance(traced, CallResult) else None),
        )

    ## Preserve parameter forwarding in call-edge argument facts.
    #  @param node Argument expression.
    #  @return ParameterSource or ordinary argument source.
    def _call_edge_argument_source(self, node):
        if isinstance(node, ast.Subscript):
            dependency = self._parameter_dependency_source(node.value)
            if isinstance(dependency, ParameterSource):
                if isinstance(node.slice, ast.Slice):
                    return ParameterSource(
                        dependency.scope,
                        dependency.name,
                        derived=True,
                        attributes=dependency.attributes,
                        derived_operation="slice",
                    )
                index = self._get_slice(node.slice)
                return ContainerItem(
                    dependency, index if index is not None else "*")
        if isinstance(node, (ast.Constant, ast.JoinedStr, ast.List,
                             ast.Tuple, ast.Set, ast.Dict)):
            python_shape = self._expression_python_shape(node)
            if python_shape is not None:
                return python_shape
        if isinstance(node, ast.Name) and self._caller_stack:
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if (binding is not None and isinstance(binding.source, SourceSet)
                    and binding.source.origin == "function_branch"):
                return binding.source
            if (self.current_scope().kind == SCOPE_COMPREHENSION
                    and node.id in self.comprehension_targets
                    and binding is not None
                    and (normalize_source(binding.source) == "local"
                         or (isinstance(
                             normalize_source(binding.source), CallResult)
                             and normalize_source(
                                 binding.source).result_source is None))):
                return UnknownSource("unresolved iterator element")
            if (binding is not None
                    and binding.binding_kind == "parameter"):
                return ParameterSource(
                    self._caller_stack[-1].qualname, node.id)
            assigned_call = self._assigned_call_sources.get(
                (id(self.current_scope()), node.id))
            if assigned_call is not None:
                return assigned_call
        imported_call = self._imported_call_result_source(node)
        if imported_call is not None:
            return imported_call
        return self._value_source(node)

    ## Preserve the exact producing call for a receiver-protocol argument.
    #  @param node Argument or return expression.
    #  @return Concrete Python shape, exact CallResult, or None.
    def _call_edge_protocol_source(self, node):
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if (binding is not None and isinstance(binding.source, SourceSet)
                    and binding.source.origin == "function_branch"):
                return binding.source
        if isinstance(node, ast.Call):
            if (_is_unshadowed_builtin_call(self, node)
                    and node.func.id in _BUILTIN_PYTHON_OWNED_RESULT
                    and node.func.id != "super"
                    and _builtin_shape_type(node.func.id) is not None):
                return PythonShape(node.func.id)
            source = self._call_edge_argument_source(node)
            shape = self._expression_python_shape(node)
            if (isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Subscript)):
                receiver = self._call_edge_argument_source(node.func.value)
                if (isinstance(receiver, ContainerItem)
                        and isinstance(receiver.container, ParameterSource)):
                    return CallResult(
                        source, display_name=ast.unparse(node.func),
                        call_lineno=node.lineno, call_col_offset=node.col_offset,
                        result_source=InstanceMethod(receiver, node.func.attr))
            chained = (isinstance(node.func, ast.Attribute)
                       and isinstance(node.func.value, ast.Call))
            if isinstance(source, CallResult) and not chained:
                if shape is not None:
                    return replace(source, result_source=shape)
                return source
            return CallResult(
                (source.callee if isinstance(source, CallResult) else source)
                or UnknownSource("unresolved return callable"),
                display_name=ast.unparse(node.func),
                call_lineno=node.lineno,
                call_col_offset=node.col_offset,
                result_source=shape or source)
        return self._expression_python_shape(node)

    ## Preserve exact fields of a callback argument tuple.
    #  @param node Candidate tuple/list expression.
    #  @return TupleSource with UnknownSource fields when needed, or None for
    #  a non-tuple expression.
    def _call_edge_tuple_source(self, node):
        if not isinstance(node, (ast.Tuple, ast.List)):
            return None
        fields = []
        for field in node.elts:
            source = normalize_source(self._call_edge_argument_source(field))
            fields.append(source or UnknownSource("unresolved callback argument"))
        return TupleSource(tuple(fields))

    ## Attach the defining module to a declaration-time call source.
    #  Default expressions are evaluated while visiting a function definition,
    #  outside the function call graph. The module fact keeps alias resolution
    #  available when that default is later propagated to a receiver.
    #  @param source Candidate argument source.
    #  @return Source with module metadata when it is a CallResult.
    def _default_argument_source(self, source):
        return self._source_with_module(source)

    ## Attach this analyzer's module to a call result when absent.
    #  @param source Candidate source value.
    #  @return Source with module metadata when applicable.
    def _source_with_module(self, source):
        source = normalize_source(source)
        if not isinstance(source, CallResult) or source.source_module:
            return source
        return CallResult(
            source.callee,
            display_name=source.display_name,
            call_lineno=source.call_lineno,
            call_col_offset=source.call_col_offset,
            source_module=self.module_name or "",
            result_source=source.result_source,
        )

    ## Return a project-local callback identity carried by one argument.
    #  @param node Call argument AST node.
    #  @return Local function or qualified self-method name, otherwise None.
    def _call_edge_callback_name(self, node):
        if isinstance(node, ast.Name):
            if (node.id in self.defined_functions
                    or node.id in self.class_methods):
                return node.id
            return None
        if (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in ("self", "cls")
                and self._class_stack
                and node.attr in self.class_methods.get(
                    self._class_stack[-1], [])):
            return self._class_stack[-1] + "." + node.attr
        return None

    ## Preserve element ownership for a call argument used as an iterable.
    #
    #  This fact is separate from ordinary argument ownership. A Python list
    #  may yield project-local or import-backed objects, so treating the list
    #  owner as the element owner would contaminate receiver classification.
    #  @param node Argument expression.
    #  @return Element source or None when the iterable is not explicit.
    def _call_edge_iterable_source(self, node):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            if not node.elts:
                return UnknownSource("empty iterable")
            return _iterable_element_source(node, self.trace_source)
        if isinstance(node, ast.Name):
            binding = self.current_scope().lookup(
                node.id, skip_parent_classes=True)
            if binding is not None:
                tuple_sources = self._iterated_append_tuple_sources.get(
                    self._binding_key(binding))
                if tuple_sources is not None:
                    return tuple_sources
                source = self._iterable_binding_sources.get(
                    self._binding_key(binding))
                if source is not None:
                    return source
                dependency = self._parameter_dependency_source(node)
                if dependency is not None:
                    return ContainerIter(dependency)
        return None

    ## Attach an explicit iterable's element source to its lexical binding.
    #
    #  Binding identity prevents a same-name container in another function
    #  from changing an already collected call edge.
    #  @param node Assignment node whose targets have already been bound.
    def _record_iterable_binding_source(self, node):
        if not isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
            return
        if not node.value.elts:
            item_source = UnknownSource("empty iterable")
        else:
            item_source = _iterable_element_source(
                node.value, self.trace_source)
        if item_source is None:
            return
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            binding = self.current_scope().bindings.get(target.id)
            if binding is not None:
                self._iterable_binding_sources[
                    self._binding_key(binding)] = item_source

    ## Resolve the result object of a builtin container method.
    #
    #  The method callable is Python-owned, but selection methods return a
    #  value from the receiver. Preserve that item source instead of
    #  contaminating the result object with the callable's owner.
    #  @param node Method call.
    #  @param receiver_kind Independently known builtin container kind.
    #  @param method_name Called method name.
    #  @return Result source, "python", or None.
    def _builtin_method_result_source(
            self, node, receiver_kind, method_name):
        if (receiver_kind == "dict"
                and method_name == "get"
                and node.args):
            receiver = node.func.value
            if isinstance(receiver, ast.Name):
                container = receiver.id
            else:
                container = self.trace_source(receiver)
            key_node = node.args[0]
            if isinstance(key_node, ast.Constant):
                key = key_node.value
            else:
                key = "*"
            selected = ContainerItem(container, key)
            if len(node.args) >= 2:
                default = _builtin_value_source(
                    node.args[1], self.trace_source)
                return make_source_set(
                    (selected, default), origin="dict_lookup")
            return selected
        return "python"

    ## Record a SymbolRef for provenance tracking.
    #  @param symbol Display name.
    #  @param source Source value.
    #  @param kind Symbol category.
    #  @param node Optional AST node for position.
    def _add_symbol_ref(self, symbol, source, kind, node=None):
        scope_name = ""
        cs = self.current_scope()
        if cs.kind != SCOPE_MODULE:
            scope_name = cs.name
        self.symbol_refs.append(SymbolRef(
            symbol=symbol,
            source=source,
            kind=kind,
            module_name=self.module_name or "",
            file_path=getattr(self, '_file_path', ""),
            scope_name=scope_name,
            lineno=getattr(node, "lineno", 0) if node is not None else 0,
            col_offset=getattr(node, "col_offset", 0) if node is not None else 0,
        ))

    ## --- API call detection ---

    ## Resolve the base of an API call for origin tracking.
    #
    #  Tries getattr(), import_module(), method resolution, and
    #  call-lookup receiver resolution in order.
    #  @param node The Call AST node.
    #  @return Base symbol, structured tuple, or None.
    def _resolve_call_base_for_api(self, node):
        # P0 (1.0.5): bare getattr() builtin calls must be classified as
        # python, not traced through the argument's provenance.  Only
        # trace through obj.getattr("name") style calls where getattr is
        # accessed as an attribute on a receiver object.
        if self._is_getattr_call(node) and not isinstance(node.func,
                                                          ast.Name):
            if self._literal_str(node.args[1]) is not None:
                g = self.trace_source(node.args[0])
                if g is not None:
                    return g
        if self._is_import_module_call(node):
            im = self._resolve_import_module_trace(node)
            if im is not None:
                return im
        base = self._resolve_methods(node)
        if base is not None:
            return base
        # 1.0.5 P1+: defaultdict(list) item kind — d[k].append(v) where
        # d = defaultdict(list) has item kind "list".
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Subscript):
                sub = node.func.value
                if isinstance(sub.value, ast.Name):
                    item_kind = self._lookup_container_kind(
                        sub.value.id, item=True)
                    if item_kind is not None:
                        return InstanceMethod(sub.value.id, node.func.attr)
        ## For chained calls (A().B()), resolve via the inner call's
        ## return source so the outer call traces to the correct library.
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Call):
            inner_source = self.trace_source(node.func.value)
            if isinstance(inner_source, str):
                rs = self.return_sources.get(inner_source)
                if rs is not None:
                    return rs
            if isinstance(inner_source, CallResult):
                if inner_source.result_source is not None:
                    return inner_source.result_source
                rs = self.return_sources.get(inner_source.callee)
                if rs is not None:
                    return rs
            if isinstance(inner_source, InstanceMethod):
                if inner_source.parameter_scope:
                    return InstanceMethod(
                        inner_source,
                        node.func.attr,
                        parameter_scope=inner_source.parameter_scope,
                        parameter_name=inner_source.parameter_name,
                    )
            if isinstance(inner_source, SourceSet):
                return inner_source
            # 1.0.5 P1: library-function return types for chained
            # calls (cdist(...).argmin(), np.log(s).diff()).
            inner_call = node.func.value
            func_top, func_name = self._resolve_func_top(inner_call.func)
            if func_top and func_top not in ("local", "python", "unknown", ""):
                ret = _match_result_owner(func_top, func_name)
                if ret:
                    return ret
                preserved = self._receiver_preserving_result_owner(
                    inner_call, func_top, func_name)
                if preserved is not None:
                    return preserved
        call_lookup_base = self.get_base(node, call_lookup=True)
        if call_lookup_base is not None:
            return call_lookup_base
        return self.get_base(node.func)

    ## Collect all prefix calls in a chained call expression.
    #
    #  For a.b().c().d(), returns [a.b(), c(), d()] in call order.
    #  @param node The outermost Call AST node.
    #  @return List of Call nodes from outermost to innermost chain, reversed.
    def _chained_prefix_calls(self, node):
        if not isinstance(node, ast.Call):
            return []
        out = []
        cur = node
        while isinstance(cur, ast.Call):
            out.append(cur)
            f = cur.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Call):
                cur = f.value
            else:
                break
        out.reverse()
        return out


    ## Collect a CallSite from the raw call data.
    #  @param expression Full call expression.
    #  @param func_name Function part.
    #  @param parameters Arguments string.
    #  @param base Base symbol or source.
    #  @param loc Dict with lineno/col_offset/end_lineno/end_col_offset.
    def _collect_call_site(self, expression, func_name, parameters,
                           base, loc):
        scope_name = ""
        cs = self.current_scope()
        if cs.kind != SCOPE_MODULE:
            scope_name = cs.name
        self.call_site_objects.append(CallSite(
            expression=expression,
            func_name=func_name,
            parameters=parameters,
            base=base,
            module_name=self.module_name or "",
            file_path=getattr(self, '_file_path', ""),
            lineno=loc.get('lineno', 0),
            col_offset=loc.get('col_offset', 0),
            end_lineno=loc.get('end_lineno', 0),
            end_col_offset=loc.get('end_col_offset', 0),
            scope_name=scope_name,
        ))

    ## Record verified owner evidence supplied to callback parameters.
    #
    #  @param node The call expression accepting a callback.
    def _collect_callback_parameter_sources(self, node):
        func_top, func_name = self._resolve_func_top(node.func)
        if not func_top or not func_name:
            return
        for (owner, name, callback_index, parameter_index), contract in (
                _CALLBACK_PARAMETER_OWNER_CONTRACTS.items()):
            if (name != func_name
                    or not (func_top == owner
                            or func_top.startswith(owner + "."))
                    or callback_index >= len(node.args)):
                continue
            callback = node.args[callback_index]
            callback_key = self._value_source(callback)
            if not isinstance(callback_key, str):
                continue
            bare_key = callback_key.rsplit(".", 1)[-1]
            params = (self.function_params.get(callback_key)
                      or self.function_params.get(bare_key, []))
            if parameter_index >= len(params):
                continue
            parameter = params[parameter_index]
            self.parameter_sources.setdefault(
                (callback_key, parameter), []).append(contract[0])

    ## Return (func_str, args_str) tuple for a Call node.
    #  @param node The Call AST node.
    #  @return Tuple of (function expression, arguments string).
    def _get_call_parts(self, node):
        func_str = ast.unparse(node.func)
        parts = [ast.unparse(a) for a in node.args]
        if node.keywords:
            for kw in node.keywords:
                if kw.arg:
                    parts.append(f"{kw.arg}={ast.unparse(kw.value)}")
                else:
                    parts.append(f"**{ast.unparse(kw.value)}")
        args_str = ", ".join(parts)
        return func_str, args_str

    ## Reconstruct a call expression as a string.
    #  @param node The Call AST node.
    #  @return String representation like "func(arg1, arg2, kw=val)".
    def get_call(self, node):
        func_str, args_str = self._get_call_parts(node)
        return f"{func_str}({args_str})"

    ## Visit a Call node and record API calls from its chained prefix calls.
    #  @param node The Call AST node.
    def visit_Call(self, node):
        self._mapping_facts.call(node)
        self._collect_argparse_destination(node)
        self._collect_callback_parameter_sources(node)
        self._record_container_append_shape(node)
        for sub in self._chained_prefix_calls(node):
            self._one_api_call(sub)
        if isinstance(node.func, ast.Name) and node.func.id in self.defined_functions:
            arg_sources = []
            protocol_arg_sources = []
            for arg in node.args:
                if isinstance(arg, ast.Attribute):
                    name = self._attribute_name(arg)
                    arg_sources.append(
                        name if name else self._call_edge_argument_source(arg))
                else:
                    arg_sources.append(self._call_edge_argument_source(arg))
                protocol_arg_sources.append(
                    self._call_edge_protocol_source(arg))
            self.call_sites.setdefault(node.func.id, []).append({
                "module": self.module_name,
                "args": arg_sources,
                "protocol_args": protocol_arg_sources,
                "lineno": node.lineno,
                "col_offset": node.col_offset,
            })
        elif isinstance(node.func, ast.Name) and node.func.id in self.class_methods:
            arg_sources = []
            protocol_arg_sources = []
            for arg in node.args:
                if isinstance(arg, ast.Attribute):
                    name = self._attribute_name(arg)
                    arg_sources.append(
                        name if name else self._call_edge_argument_source(arg))
                else:
                    arg_sources.append(self._call_edge_argument_source(arg))
                protocol_arg_sources.append(
                    self._call_edge_protocol_source(arg))
            self.call_sites.setdefault(node.func.id + ".__init__", []).append({
                "module": self.module_name,
                "args": arg_sources,
                "protocol_args": protocol_arg_sources,
                "lineno": node.lineno,
                "col_offset": node.col_offset,
            })
        self.generic_visit(node)

    ## Visit an Attribute access node and record the top-level origin.
    #  @param node The Attribute AST node.
    def visit_Attribute(self, node):
        attr_string = ast.unparse(node)
        name = self._attribute_name(node)
        if name and name in self.symbols.direct:
            base = name
        else:
            base = self.get_base(node)
        if base:
            top = self.symbols.get_top(base)
            if top:
                self.attr_accesses.append({
                    'attr': attr_string,
                    'top': top,
                    'chain': self.symbols.get_chain(base)
                })
        self.generic_visit(node)

    ## Visit a With node and bind context-variable aliases.
    #  @param node The With AST node.
    def visit_With(self, node):
        for item in node.items:
            source = self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._target_to_source(item.optional_vars, source)
        self.generic_visit(node)

    ## Visit an AsyncWith node and bind context-variable aliases.
    #  @param node The AsyncWith AST node.
    def visit_AsyncWith(self, node):
        for item in node.items:
            source = self.trace_source(item.context_expr)
            if item.optional_vars is not None:
                self._target_to_source(item.optional_vars, source)
        self.generic_visit(node)
