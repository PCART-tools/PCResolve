## @package pcresolve.call_result_resolution
#  Resolve ownership for structured call-result sources.
#
#  This mixin keeps the call-result state machine separate from project
#  orchestration while delegating project indexes and recursive resolution
#  to ProjectAnalyzer.

from .sources import (
    CallResult, ContainerItem, DerivedResult, InstanceMethod, PythonShape,
    SourceSet, UnknownSource, normalize_source, source_display,
)


## Resolve CallResult ownership through project-level provenance facts.
class CallResultResolutionMixin:
    ## Resolve ownership for the result of one call expression.
    #
    #  @param module Module containing the call expression.
    #  @param direct_source Full CallResult source and result metadata.
    #  @param callee Callee source extracted by the structured-source dispatcher.
    #  @param callee_display Preferred callee spelling for provenance output.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Structured-source recursion guard.
    #  @return Resolved display, module, and owner tuple.
    def _resolve_call_result_source(self, module, direct_source, callee,
                                    callee_display, tracers, _seen):
        display = f"{callee_display or callee}()"
        if isinstance(callee, ContainerItem):
            resolved = self._container_item_call_result(
                module, callee, callee_display, tracers, _seen)
            if resolved is not None:
                return resolved
        explicit = self._explicit_call_result_source(
            module, direct_source, display, tracers, _seen)
        if explicit is not None:
            return explicit
        callee_source = normalize_source(callee)
        if (isinstance(callee_source, InstanceMethod)
                and callee_source.parameter_scope):
            return (display, module, "unknown")
        local_classes = self._local_class_from_method_result(
            module, direct_source, tracers)
        if len(local_classes) == 1:
            return (display, local_classes[0][0], local_classes[0][1])
        if len(local_classes) > 1:
            return (display, module, "unknown")
        bounded = self._bounded_call_result_candidates(
            module, direct_source, tracers, _seen=set(_seen))
        if bounded is not None:
            bounded_top = self._bounded_candidates_top(bounded)
            bounded_module = self._bounded_owner_module(
                bounded_top, module, tracers)
            return (display, bounded_module, bounded_top)
        cr_lineno = getattr(direct_source, 'call_lineno', 0) or 0
        cr_col = getattr(direct_source, 'call_col_offset', 0) or 0
        if isinstance(callee, SourceSet):
            primary = self._resolve_sourceset_primary(module, callee, tracers)
            if primary:
                return (display, module, primary)
            return (display, module, "local")
        cur_module, cur_symbol = self._initial_call_result_target(
            module, callee, tracers, _seen)
        return self._resolve_call_result_summary_chain(
            module, cur_module, cur_symbol, callee, callee_display,
            display, tracers, _seen, cr_lineno, cr_col)

    ## Resolve a structured container item used as the called object.
    def _container_item_call_result(
            self, module, callee, callee_display, tracers, _seen):
        resolved = self._resolve_structured_source(
            module, callee, tracers, _seen=set(_seen))
        if resolved is None:
            return None
        _, callee_module, callee_symbol = resolved
        callee_top = self._top_source(
            callee_module, callee_symbol, tracers, _seen=set(_seen))
        if not callee_top:
            return None
        return (
            f"{callee_display or source_display(callee)}()",
            callee_module,
            callee_top)

    ## Resolve an explicit result_source carried by a CallResult.
    def _explicit_call_result_source(
            self, module, direct_source, display, tracers, _seen):
        explicit = direct_source.result_source
        if explicit is None:
            return None
        if isinstance(explicit, UnknownSource):
            return (display, module, "unknown")
        if isinstance(explicit, PythonShape) or explicit == "python":
            return (display, module, "python")
        if isinstance(explicit, DerivedResult):
            if explicit.kind == "iterator":
                return (display, module, "unknown")
            candidates = self._origin_candidates(
                module, explicit, tracers, _seen=set(_seen))
            unique = self._dedupe_list([
                candidate for candidate in candidates
                if candidate not in ("", None)
            ])
            if len(unique) == 1 and unique[0] != "unknown":
                return (display, module, unique[0])
            bounded = self._bounded_call_result_candidates(
                module, direct_source, tracers, _seen=set(_seen))
            if bounded is not None:
                bounded_top = self._bounded_candidates_top(bounded)
                bounded_module = self._bounded_owner_module(
                    bounded_top, module, tracers)
                return (display, bounded_module, bounded_top)
            return (display, module, "unknown")
        if (isinstance(explicit, str)
                and explicit not in ("local", "unknown", "")):
            return (display, module, explicit)
        return None

    ## Locate the initial project module and symbol for return lookup.
    def _initial_call_result_target(
            self, module, callee, tracers, _seen):
        gs = getattr(self, '_call_searched_global', None)
        if gs is not None:
            if (module, callee) in gs:
                callee_chain = [callee]
            else:
                gs.add((module, callee))
                callee_chain = self.trace_symbol(
                    module, callee, tracers, set(_seen))
        else:
            callee_chain = self.trace_symbol(
                module, callee, tracers, set(_seen))
        def_module = module
        for item in reversed(callee_chain):
            if isinstance(item, str) and self.is_local(item):
                def_module = item
                break
        cur_module = def_module
        cur_symbol = callee
        if (isinstance(callee, str)
                and "." in callee
                and callee not in tracers):
            parts = callee.split(".")
            for index in range(len(parts) - 1, 0, -1):
                candidate_module = ".".join(parts[:index])
                if candidate_module in tracers:
                    cur_module = candidate_module
                    cur_symbol = ".".join(parts[index:])
                    break
        return cur_module, cur_symbol

    ## Follow local return summaries until ownership is resolved or cycles.
    def _resolve_call_result_summary_chain(
            self, module, cur_module, cur_symbol, callee, callee_display,
            display, tracers, _seen, call_lineno, call_col_offset):
        seen = {(cur_module, cur_symbol)}
        while True:
            tr = tracers.get(cur_module)
            rs = tr.return_sources.get(cur_symbol) if tr else None
            if rs is None and tr is not None:
                display_name = callee_display or ""
                cur_is_simple = (not isinstance(cur_symbol, str)
                                 or "." not in cur_symbol)
                if "." in display_name and cur_is_simple:
                    func_from_display = display_name.rsplit(".", 1)[-1]
                    rs = tr.return_sources.get(func_from_display)
                    if rs is None:
                        mod_tracer = tracers.get(module)
                        if mod_tracer is not None:
                            first_seg = display_name.split(".")[0]
                            sd = mod_tracer.symbols.direct.get(first_seg)
                            if isinstance(sd, str) and sd in tracers:
                                cur_module = sd
                                tr = tracers[cur_module]
                                rs = tr.return_sources.get(func_from_display)
            rs = normalize_source(rs)
            if isinstance(rs, SourceSet):
                resolved = self._call_result_sourceset_source(
                    cur_module, cur_symbol, rs, display, tracers,
                    _seen, call_lineno, call_col_offset)
                if resolved is not None:
                    return resolved
            if rs is None:
                cg_ret = self._lookup_cg_return_source(cur_module, cur_symbol)
                if cg_ret is not None:
                    return (display, module, cg_ret)
                return (display, cur_module, cur_symbol)
            if isinstance(rs, str):
                return self._call_result_string_source(
                    cur_module, cur_symbol, rs, display, tracers,
                    call_lineno, call_col_offset)
            rs = normalize_source(rs)
            if isinstance(rs, CallResult):
                next_chain = self.trace_symbol(
                    cur_module, rs.callee, tracers, set())
                cur_symbol = rs.callee
                for item in reversed(next_chain):
                    if isinstance(item, str) and self.is_local(item):
                        cur_module = item
                        break
                if (cur_module, cur_symbol) in seen:
                    return (display, cur_module, cur_symbol)
                seen.add((cur_module, cur_symbol))
                continue
            break
        return (display, cur_module, cur_symbol)

    ## Resolve one SourceSet return summary when its branches converge.
    def _call_result_sourceset_source(
            self, module, symbol, source_set, display, tracers,
            _seen, call_lineno, call_col_offset):
        candidates = self._dedupe_list([
            candidate for candidate in self._origin_candidates(
                module, source_set, tracers, _seen=set(_seen))
            if candidate not in ("", None)
        ])
        if candidates == ["python"]:
            return (display, module, "python")
        concrete = [
            candidate for candidate in candidates
            if candidate != "unknown"]
        if ("python" in concrete
                and any(candidate not in ("python", "local")
                        for candidate in concrete)):
            return (display, module, "unknown")
        primary = self._resolve_sourceset_primary(
            module, source_set, tracers)
        if primary:
            return (display, module, primary)
        for source in source_set.sources:
            if isinstance(source, str):
                return self._call_result_string_source(
                    module, symbol, source, display, tracers,
                    call_lineno, call_col_offset)
            if isinstance(source, CallResult):
                return (display, module, source.callee)
        return None

    ## Resolve a string return source through exact call-edge arguments.
    def _call_result_string_source(
            self, module, symbol, source, display, tracers,
            call_lineno, call_col_offset):
        argument_source = self._resolve_param_to_arg(
            module, symbol, source, tracers,
            call_lineno=call_lineno,
            call_col_offset=call_col_offset)
        if argument_source is not None:
            argument_source = normalize_source(argument_source)
            if isinstance(argument_source, CallResult):
                return (display, module, argument_source.callee)
            if isinstance(argument_source, str):
                return (display, module, argument_source)
        return (display, module, source)
