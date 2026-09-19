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

        ## Record CallEdge fact for Phase 7B-full call graph.
        if self._caller_stack:
            caller = self._caller_stack[-1]
            ## Collect receiver source for obj.method() calls.
            receiver_source = None
            if isinstance(node.func, ast.Attribute):
                receiver = node.func.value
                if (isinstance(receiver, ast.Name)
                        and receiver.id in ("self", "cls")):
                    receiver_source = self.get_base(receiver)
                else:
                    receiver_source = self._call_edge_argument_source(
                        receiver)
            ## Collect arg sources.  Ordinary positional and keyword
            #  arguments stay in the existing maps; starred expansions are
            #  retained separately so cross-file binding can respect the
            #  callee signature instead of treating a pack as one value.
            arg_sources = {"pos": {}, "kw": {}}
            protocol_arg_sources = {"pos": {}, "kw": {}}
            iterable_arg_sources = {"pos": {}, "kw": {}}
            star_arg_sources = {}
            positional_index = 0
            for arg in node.args:
                if isinstance(arg, ast.Starred):
                    star_src = self._call_edge_argument_source(arg.value)
                    if star_src is not None:
                        star_arg_sources[positional_index] = star_src
                    positional_index = None
                    continue
                arg_src = self._call_edge_argument_source(arg)
                if arg_src is not None:
                    if positional_index is not None:
                        arg_sources["pos"][positional_index] = arg_src
                protocol_src = self._call_edge_protocol_source(arg)
                if protocol_src is not None:
                    if positional_index is not None:
                        protocol_arg_sources["pos"][positional_index] = protocol_src
                iterable_src = self._call_edge_iterable_source(arg)
                if iterable_src is not None:
                    if positional_index is not None:
                        iterable_arg_sources["pos"][positional_index] = iterable_src
                if positional_index is not None:
                    positional_index += 1
            star_kwarg_sources = []
            for kw in getattr(node, "keywords", []) or []:
                if kw.arg is None:
                    star_src = self._call_edge_argument_source(kw.value)
                    if star_src is not None:
                        star_kwarg_sources.append(star_src)
                    continue
                arg_src = (
                    self._call_edge_argument_source(kw.value)
                    if kw.arg else None)
                if arg_src is not None and kw.arg:
                    arg_sources["kw"][kw.arg] = arg_src
                protocol_src = (
                    self._call_edge_protocol_source(kw.value)
                    if kw.arg else None)
                if protocol_src is not None and kw.arg:
                    protocol_arg_sources["kw"][kw.arg] = protocol_src
                iterable_src = (
                    self._call_edge_iterable_source(kw.value)
                    if kw.arg else None)
                if iterable_src is not None and kw.arg:
                    iterable_arg_sources["kw"][kw.arg] = iterable_src
            ## Consume assigned_to only for the top-level RHS call.
            assigned = self._pending_call_targets_by_node.pop(id(node), [])
            callback_args = {}
            for index, arg in enumerate(node.args):
                callback_name = self._call_edge_callback_name(arg)
                if callback_name:
                    callback_args[index] = callback_name
            callback_bindings = []
            target_names = {
                kw.value.id for kw in getattr(node, "keywords", []) or []
                if kw.arg == "target" and isinstance(kw.value, ast.Name)
            }
            args_keyword = next(
                (kw.value for kw in getattr(node, "keywords", []) or []
                 if kw.arg == "args"), None)
            callback_source = self._call_edge_tuple_source(args_keyword)
            if callback_source is not None:
                callback_bindings = [
                    {"callback": target, "args": callback_source}
                    for target in sorted(target_names)
                ]
            edge = CallEdge(
                caller=caller,
                callee=base,
                callee_name=func_name or "",
                callee_source=self._call_edge_callee_source(node.func),
                receiver_source=receiver_source,
                arg_sources=arg_sources,
                star_arg_sources=star_arg_sources,
                star_kwarg_sources=star_kwarg_sources,
                callback_args=callback_args,
                callback_bindings=callback_bindings,
                protocol_arg_sources=protocol_arg_sources,
                iterable_arg_sources=iterable_arg_sources,
                assigned_to=assigned,
                call_lineno=node.lineno,
                call_col_offset=node.col_offset,
                source_span=SourceSpan.from_ast(getattr(self, '_file_path', ''), node),
            )
            self.module_cg.edges.append(edge)
            mapping_value = self._mapping_facts.value(node.func)
            if mapping_value is not None and mapping_value.selected:
                self._mapping_edges.append((edge, mapping_value))

        if isinstance(node.func, ast.Name):
            direct_name = node.func.id
        else:
            direct_name = None

        scope_name = ""
        cs = self.current_scope()
        if cs.kind != SCOPE_MODULE:
            scope_name = cs.name
        loc = {
            'func_name': func_name,
            'parameters': parameters,
            'lineno': node.lineno,
            'col_offset': node.col_offset,
            'end_lineno': getattr(node, 'end_lineno', 0) or 0,
            'end_col_offset': getattr(node, 'end_col_offset', 0) or 0,
            'scope_name': scope_name,
        }
        if isinstance(normalize_source(base), SuperMethod):
            # Snapshot the class-definition import path, before later
            # rebinding or another same-named class can replace the evidence.
            loc['super_base_path'] = None
            receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
            if (isinstance(receiver, ast.Call)
                    and isinstance(receiver.func, ast.Name)
                    and receiver.func.id == 'super'
                    and not receiver.args and not receiver.keywords
                    and _is_unshadowed_builtin_call(self, receiver)
                    and cs.kind == SCOPE_FUNCTION
                    and cs.parent is not None and cs.parent.kind == SCOPE_CLASS
                    and self._super_base_path_stack):
                base_path, decorator_module = self._super_base_path_stack[-1]
                loc['super_base_path'] = base_path
                loc['super_decorator_module'] = decorator_module
        # 1.0.5 P0: snapshot call_assign_funcs for dotted calls so
        # cross-file _resolve_func_name reads the pre-assignment
        # state, not the final map that may include later
        # reassignments.
        if func_name and '.' in func_name:
            first = func_name.split('.')[0]
            loc['call_assign_func'] = self.call_assign_funcs.get(first)
            binding = self.current_scope().lookup(
                first, skip_parent_classes=True)
            if (binding is not None
                    and binding.binding_kind == "import"
                    and binding.scope_kind != SCOPE_MODULE):
                loc["call_import_source"] = (
                    self._import_binding_sources.get(
                        self._binding_key(binding))
                    or binding.source
                )

        # The callable identity of an unshadowed builtin is independent of
        # the object it returns.  Record it before return-value provenance can
        # introduce an unrelated same-name assignment from another scope.
        if direct_name and _is_unshadowed_builtin_call(self, node):
            record = {
                'api': api_string,
                'top': 'python',
                'chain': ['python'],
                'base': direct_name,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    direct_name, loc)
            return

        # A concrete receiver kind determines the callable owner even when
        # legacy base resolution represents the receiver as a plain string.
        # This covers names, self attributes, and homogeneous subscript items.
        receiver_kind = self._call_receiver_container_kind(node)
        method_name = (
            node.func.attr if isinstance(node.func, ast.Attribute) else "")
        if (receiver_kind is not None
                and _has_builtin_shape_method(receiver_kind, method_name)):
            loc["receiver_container_kind"] = receiver_kind
            record = {
                'api': api_string,
                'top': 'python',
                'chain': ['python'],
                'base': base,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
            return

        if isinstance(base, UnknownSource):
            record = {
                'api': api_string,
                'top': 'unknown',
                'chain': ['unknown'],
                'base': base,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
            return

        if isinstance(base, CallResult):
            # Resolve top through the callee so s.get() shows 'requests'
            # instead of 'requests()' when s = Session().
            callee = base.callee
            ## 1.0.5 P2: explicit result_source carries result-object ownership.
            #  When set, it overrides callee-based tracing — the callable's
            #  identity is determined by what the called function returns,
            #  not who was called.
            rs_explicit = getattr(base, 'result_source', None)
            if rs_explicit is not None:
                if isinstance(rs_explicit, UnknownSource):
                    top = "unknown"
                elif isinstance(rs_explicit, PythonShape):
                    top = "python"
                elif rs_explicit == "python":
                    top = "python"
                elif is_structured_source(rs_explicit):
                    # Structured: defer to cross_file for resolution.
                    # In single-file, use source_display as placeholder.
                    top = source_display(base)
                else:
                    # String source — direct ownership.
                    top = str(rs_explicit)
            elif isinstance(callee, str):
                rs = self.return_sources.get(callee)
                if rs is not None:
                    resolved = normalize_source(rs)
                    if isinstance(resolved, CallResult):
                        inner_callee = resolved.callee
                        if isinstance(inner_callee, str):
                            callee = inner_callee
                    elif isinstance(resolved, SourceSet):
                        top = source_display(base)
                        chain = [top]
                        record = {
                            'api': api_string,
                            'top': top,
                            'chain': chain,
                            'base': base,
                            'direct_name_callee': direct_name,
                        }
                        record.update(loc)
                        self.api_calls.append(record)
                        self._collect_call_site(api_string, func_name, parameters,
                                                base, loc)
                        return
                top = self.symbols.get_top(callee) or source_display(base)
            else:
                top = source_display(base)
            chain = [source_display(base)]
            record = {
                'api': api_string,
                'top': top,
                'chain': chain,
                'base': base,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
            return

        if (isinstance(base, tuple)
                or isinstance(base, (
                    ContainerItem, ContainerIter, InstanceMethod,
                    SuperMethod, SourceSet))):
            # Unresolved compare receiver: owner cannot be determined.
            # Emit as unknown so the call is collected but not
            # misattributed to local.
            if (isinstance(base, InstanceMethod)
                    and isinstance(base.receiver, str)
                    and base.receiver == "__unresolved_compare__"):
                display = "unknown"
                chain = ["unknown"]
                record = {
                    'api': api_string,
                    'top': display,
                    'chain': chain,
                    'base': base,
                    'direct_name_callee': direct_name,
                }
                record.update(loc)
                self.api_calls.append(record)
                self._collect_call_site(api_string, func_name, parameters,
                                        base, loc)
                return

            display = source_display(base)
            if isinstance(base, InstanceMethod) and isinstance(base.receiver, str):
                top_from_receiver = self.symbols.get_top(base.receiver)
                # 1.0.5 P1: builtin container methods on receivers
                # whose container kind is known.  The receiver may be
                # local via get_top, scope binding, or item kind
                # (defaultdict(list) — receiver traces to collections
                # but item kind is list).
                #
                rec_local = (top_from_receiver == "local")
                if not rec_local:
                    binding = self.current_scope().lookup(base.receiver)
                    if (binding is not None
                            and binding.source == "local"):
                        rec_local = True
                # Use the exact call receiver shape to distinguish
                # d[k].append() item metadata from d.append(). Lexical
                # binding metadata prevents same-name scope leakage.
                kind = self._call_receiver_container_kind(node)
                if rec_local or kind is not None:
                    if (kind is not None
                            and _has_builtin_shape_method(kind, base.method)):
                        display = "python"
                        # Record kind at call-site time so cross-file
                        # phase doesn't see later invalidation.
                        loc["receiver_container_kind"] = kind
                    elif rec_local and not base.parameter_scope:
                        display = "local"
                    else:
                        display = display  # keep source_display default
            chain = [display] if display else []
            record = {
                'api': api_string,
                'top': display,
                'chain': chain,
                'base': base,
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
            return

        # Handle a lexical binding that resolves to a local value.
        if base == "local":
            record = {
                'api': api_string,
                'top': 'local',
                'chain': ['local'],
                'base': 'local',
                'direct_name_callee': direct_name,
            }
            record.update(loc)
            self.api_calls.append(record)
            self._collect_call_site(api_string, func_name, parameters,
                                    base, loc)
            return

        top = self.symbols.get_top(base)
        if not top:
            return

        record = {
            'api': api_string,
            'top': top,
            'chain': self.symbols.get_chain(base),
            'base': base,
            'direct_name_callee': direct_name,
        }
        record.update(loc)
        self.api_calls.append(record)
        self._collect_call_site(api_string, func_name, parameters,
                                base, loc)
