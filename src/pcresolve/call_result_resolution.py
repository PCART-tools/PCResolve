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
        # A call can be made through a structured receiver source, such
        # as a DataFrame column selected with ``df["col"]``. Resolve that
        # source before ordinary symbol tracing so reassignment preserves
        # the receiver owner instead of collapsing to a local callable.
        if isinstance(callee, ContainerItem):
            resolved_callee = self._resolve_structured_source(
                module, callee, tracers, _seen=set(_seen))
            if resolved_callee is not None:
                _, callee_module, callee_symbol = resolved_callee
                callee_top = self._top_source(
                    callee_module, callee_symbol, tracers,
                    _seen=set(_seen))
                if callee_top:
                    return (
                        f"{callee_display or source_display(callee)}()",
                        callee_module,
                        callee_top,
                    )
        ## 1.0.5 P2: explicit result_source carries result-object ownership.
        rs_explicit = getattr(direct_source, 'result_source', None)
        if rs_explicit is not None:
            if isinstance(rs_explicit, UnknownSource):
                return (f"{callee_display or callee}()", module, "unknown")
            if isinstance(rs_explicit, PythonShape):
                return (f"{callee_display or callee}()", module, "python")
            if rs_explicit == "python":
                return (f"{callee_display or callee}()", module, "python")
            if isinstance(rs_explicit, DerivedResult):
                ## 1.0.5 P2: resolve derived result from operands.
                if rs_explicit.kind == "iterator":
                    return (f"{callee_display or callee}()",
                            module, "unknown")
                candidates = self._origin_candidates(
                    module, rs_explicit, tracers,
                    _seen=set(_seen))
                unique = self._dedupe_list([
                    candidate for candidate in candidates
                    if candidate not in ("", None)
                ])
                if len(unique) == 1 and unique[0] != "unknown":
                    return (f"{callee_display or callee}()",
                            module, unique[0])
                # The placeholder may describe a method on a forwarded
                # parameter.  Its exact local method summary can still
                # prove the returned object at this call position.
                bounded = self._bounded_call_result_candidates(
                    module, direct_source, tracers,
                    _seen=set(_seen))
                if bounded is not None:
                    bounded_top = self._bounded_candidates_top(bounded)
                    bounded_module = self._bounded_owner_module(
                        bounded_top, module, tracers)
                    return (
                        f"{callee_display or callee}()",
                        bounded_module,
                        bounded_top,
                    )
                return (f"{callee_display or callee}()", module, "unknown")
            elif isinstance(rs_explicit, str) and rs_explicit not in ("local", "unknown", ""):
                # Module name string (from __import__("literal")) or
                # other explicit library name.  This IS the top_library.
                return (f"{callee_display or callee}()", module, rs_explicit)
        ## A method on an unconstrained function parameter does not prove
        ## the owner of its returned object.  Keep chained calls unknown
        ## unless an explicit result source above already resolved it.
        callee_source = normalize_source(callee)
        if (isinstance(callee_source, InstanceMethod)
                and callee_source.parameter_scope):
            return (f"{callee_display or callee}()", module, "unknown")
        local_classes = self._local_class_from_method_result(
            module, direct_source, tracers)
        if len(local_classes) == 1:
            return (
                f"{callee_display or callee}()",
                local_classes[0][0],
                local_classes[0][1],
            )
        if len(local_classes) > 1:
            return (f"{callee_display or callee}()", module, "unknown")
        bounded = self._bounded_call_result_candidates(
            module, direct_source, tracers, _seen=set(_seen))
        if bounded is not None:
            bounded_top = self._bounded_candidates_top(bounded)
            bounded_module = self._bounded_owner_module(
                bounded_top, module, tracers)
            return (
                f"{callee_display or callee}()",
                bounded_module,
                bounded_top,
            )
        cr_lineno = getattr(direct_source, 'call_lineno', 0) or 0
        cr_col = getattr(direct_source, 'call_col_offset', 0) or 0
        if isinstance(callee, SourceSet):
            primary = self._resolve_sourceset_primary(module, callee, tracers)
            if primary:
                return (f"{callee_display or callee}()", module, primary)
            return (f"{callee_display or callee}()", module, "local")
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
        # A direct import-from call preserves its qualified local symbol,
        # for example factory.create_app or provider.DecoderHolder.
        # Split the longest project-module prefix before looking up local
        # return summaries; external qualified names remain untouched.
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
        seen = {(cur_module, cur_symbol)}
        while True:
            tr = tracers.get(cur_module)
            rs = tr.return_sources.get(cur_symbol) if tr else None
            # 1.0.5 P1: if callee is a module alias (import factory
            # as f; f.create_app()), resolve the function name from
            # display_name and look up return_sources in the target
            # module (via symbols.direct).
            if rs is None and tr is not None:
                display_name = callee_display or ''
                cur_is_simple = (not isinstance(cur_symbol, str)
                                 or '.' not in cur_symbol)
                if '.' in display_name and cur_is_simple:
                    func_from_display = display_name.rsplit('.', 1)[-1]
                    rs = tr.return_sources.get(func_from_display)
                    # If not found, try the resolved module from
                    # symbols.direct (e.g. f → factory).
                    if rs is None:
                        mod_tracer = tracers.get(module)
                        if mod_tracer is not None:
                            first_seg = display_name.split('.')[0]
                            sd = mod_tracer.symbols.direct.get(first_seg)
                            if isinstance(sd, str) and sd in tracers:
                                cur_module = sd
                                tr = tracers[cur_module]
                                rs = tr.return_sources.get(func_from_display)
            rs = normalize_source(rs)
            if isinstance(rs, SourceSet):
                return_candidates = self._dedupe_list([
                    candidate for candidate in self._origin_candidates(
                        cur_module, rs, tracers, _seen=set(_seen))
                    if candidate not in ("", None)
                ])
                if return_candidates == ["python"]:
                    return (f"{callee_display or callee}()",
                            cur_module, "python")
                concrete_returns = [
                    candidate for candidate in return_candidates
                    if candidate != "unknown"
                ]
                if ("python" in concrete_returns
                        and any(candidate not in ("python", "local")
                                for candidate in concrete_returns)):
                    return (f"{callee_display or callee}()",
                            cur_module, "unknown")
                ## 7B-full PR7-final: check primary convergence first
                ## so that "return" origin can pick import-backed library even
                ## when local sources are present.
                primary = self._resolve_sourceset_primary(
                    cur_module, rs, tracers)
                if primary:
                    return (f"{callee_display or callee}()",
                            cur_module, primary)
                for src in rs.sources:
                    if isinstance(src, str):
                        arg_src = self._resolve_param_to_arg(
                            cur_module, cur_symbol, src, tracers,
                            call_lineno=cr_lineno, call_col_offset=cr_col)
                        if arg_src is not None:
                            arg_src = normalize_source(arg_src)
                            if isinstance(arg_src, CallResult):
                                return (f"{callee_display or callee}()",
                                        cur_module, arg_src.callee)
                            if isinstance(arg_src, str):
                                return (f"{callee_display or callee}()",
                                        cur_module, arg_src)
                        return (f"{callee_display or callee}()", cur_module, src)
                    if isinstance(src, CallResult):
                        return (f"{callee_display or callee}()", cur_module, src.callee)
            if rs is None:
                ## 7B-full PR2: try call-graph return source before giving up.
                cg_ret = self._lookup_cg_return_source(cur_module, cur_symbol)
                if cg_ret is not None:
                    return (f"{callee_display or callee}()", module, cg_ret)
                return (f"{callee_display or callee}()", cur_module, cur_symbol)
            if isinstance(rs, str):
                arg_src = self._resolve_param_to_arg(
                    cur_module, cur_symbol, rs, tracers,
                    call_lineno=cr_lineno, call_col_offset=cr_col)
                if arg_src is not None:
                    arg_src = normalize_source(arg_src)
                    if isinstance(arg_src, CallResult):
                        return (f"{callee_display or callee}()",
                                cur_module, arg_src.callee)
                    if isinstance(arg_src, str):
                        return (f"{callee_display or callee}()",
                                cur_module, arg_src)
                return (f"{callee_display or callee}()", cur_module, rs)
            rs = normalize_source(rs)
            if isinstance(rs, CallResult):
                next_chain = self.trace_symbol(cur_module, rs.callee, tracers, set())
                cur_symbol = rs.callee
                for item in reversed(next_chain):
                    if isinstance(item, str) and self.is_local(item):
                        cur_module = item
                        break
                if (cur_module, cur_symbol) in seen:
                    return (f"{callee_display or callee}()", cur_module, cur_symbol)
                seen.add((cur_module, cur_symbol))
                continue
            break
        return (f"{callee_display or callee}()", cur_module, cur_symbol)
