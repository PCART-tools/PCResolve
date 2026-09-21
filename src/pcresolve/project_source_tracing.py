## @package pcresolve.project_source_tracing
#  Cross-file receiver, return, attribute, and final-source tracing.

from .builtin_ownership import _is_builtin
from .sources import (
    CallResult, InstanceMethod, PythonShape, SourceSet, normalize_source,
)


_NO_TRACE_CHAIN = object()


## Project source-tracing behavior mixed into ProjectAnalyzer.
class ProjectSourceTracingMixin:
    ## Unify receiver object ownership lookup through a single entry point.
    #
    #  Checks the receiver's provenance in symbols.direct and traces
    #  the callee / import alias to determine the owning library.
    #  Currently covers factory return tracing (A1) and import alias
    #  resolution (Case B).  Constructor provenance (A2) is gated on
    #  single-file callee naming and will activate once call_lookup
    #  returns the alias name rather than the module path.
    #
    #  @param module The current module.
    #  @param receiver The receiver variable name.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param tracers Dict of module_name → SingleFileAnalyzer.
    #  @return Top library name, or None.
    def _resolve_receiver_object_top(self, module, receiver, tracer, tracers):
        sd = normalize_source(tracer.symbols.direct.get(receiver))
        if sd is None:
            return None
        # Case A: CallResult — receiver was created by a call.
        # Try factory return tracing first, then constructor provenance.
        if isinstance(sd, CallResult) and isinstance(sd.callee, str):
            callee = sd.callee
            # A1: Factory return tracing (local functions with return_sources).
            top = self._resolve_receiver_with_return_sources(
                callee, module, tracers, set())
            if top and top not in ("local", "python", "unknown", ""):
                return top
            # A2: Constructor provenance.
            # The callee may be a simple name resolvable through symbols.direct
            # (e.g. from ext.api import Session; s = Session() → callee="Session").
            if isinstance(callee, str) and '.' not in callee:
                callee_sd = normalize_source(tracer.symbols.direct.get(callee))
                if isinstance(callee_sd, str) and callee_sd not in ("local", "python", ""):
                    top = self._top_source(module, callee_sd, tracers)
                    if top and top not in ("local", "python", "unknown", ""):
                        return top
            return None
        # Case B: Import alias (e.g. from factory import create_app).
        if isinstance(sd, str) and sd not in ("local", "python", ""):
            return self._resolve_receiver_with_return_sources(
                receiver, module, tracers, set())
        return None

    ## Resolve a receiver name through cross-file return_sources.
    #
    #  1.0.5 P1: supports app.test_client() → flask when app traces
    #  to a CallResult (local or imported factory function) whose
    #  return_sources trace to an import-backed library.
    #
    #  Handles:
    #    from factory import create_app → callee="create_app"
    #    import factory → callee="factory.create_app"
    #    import factory as f → callee="f.create_app"
    #
    #  @param callee The CallResult callee name (e.g. "create_app").
    #  @param module Current module.
    #  @param tracers Dict of module_name → SingleFileAnalyzer.
    #  @param _visited Already-visited set for cycle detection.
    #  @return Top library name or None.
    def _resolve_receiver_with_return_sources(self, callee, module, tracers, _visited):
        if not isinstance(callee, str):
            return None
        if (module, callee) in _visited:
            return None
        _visited.add((module, callee))

        # Split dotted callee to find defining module and function name.
        # factory.create_app → target_module="factory", func="create_app"
        # pkg.factory.create_app → target_module="pkg.factory", func="create_app"
        parts = callee.split('.')
        func = parts[-1]
        target_mod = None
        for i in range(len(parts) - 1, 0, -1):
            candidate_mod = '.'.join(parts[:i])
            if candidate_mod in tracers:
                target_mod = candidate_mod
                break

        if target_mod is None:
            # Simple name: check import_from_symbols first so aliased
            # imports resolve to the real function name.
            # from factory import make_session as cross_make
            #   → import_from_symbols["cross_make"] = "factory.make_session"
            tracer = tracers.get(module)
            if tracer is not None:
                imported = getattr(tracer, "import_from_symbols", {}).get(callee)
                if imported:
                    imported_parts = imported.split(".")
                    for i in range(len(imported_parts) - 1, 0, -1):
                        candidate_mod = ".".join(imported_parts[:i])
                        if candidate_mod in tracers:
                            target_mod = candidate_mod
                            func = ".".join(imported_parts[i:])
                            break
            if target_mod is None and tracer is not None:
                sd = tracer.symbols.direct.get(callee)
                if isinstance(sd, str) and sd in tracers:
                    target_mod = sd

        if target_mod is None:
            target_mod = module

        target_tracer = tracers.get(target_mod)
        if target_tracer is None:
            return None

        # Check return_sources for the function in the defining module
        rs = target_tracer.return_sources.get(func)
        if rs is not None:
            rs_norm = normalize_source(rs)
            sources = rs_norm.sources if isinstance(rs_norm, SourceSet) else [rs_norm]
            for s in sources:
                s = normalize_source(s)
                if isinstance(s, CallResult) and isinstance(s.callee, str):
                    top = self._top_source(target_mod, s.callee, tracers)
                    if top and top not in ("local", "python", "unknown", ""):
                        return top
        return None

    ## Try to resolve a local class method to an external source.
    #
    #  Checks whether the method's return_sources trace to a constructor
    #  parameter that has external provenance via call-site arguments.
    #  @param module The current module.
    #  @param class_name The local class name.
    #  @param method_name The method being called.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return External library name, or None.
    def _resolve_local_method_to_external(self, module, class_name,
                                           method_name, receiver,
                                           tracer, tracers):
        ## Check qualname first so class methods don't share bare keys.
        qkey = class_name + "." + method_name
        rs = tracer.return_sources.get(qkey)
        if not rs:
            rs = tracer.return_sources.get(method_name)
        if not rs:
            return None
        rs = normalize_source(rs)
        sources = rs.sources if isinstance(rs, SourceSet) else [rs]
        for src in sources:
            if isinstance(src, InstanceMethod):
                param_name = src.receiver
                if isinstance(param_name, str):
                    ctor_key = class_name + ".__init__"
                    ctor_params = (tracer.function_params.get("__init__", [])
                                   or tracer.function_params.get(ctor_key, []))
                    if param_name in ctor_params:
                        param_idx = ctor_params.index(param_name)
                        call_sites = (tracer.call_sites.get("__init__", [])
                                      or tracer.call_sites.get(ctor_key, []))
                        match_ln, match_col = self._receiver_ctor_pos(
                            receiver, tracer)
                        matched = None
                        for cs in call_sites:
                            if param_idx >= len(cs.get("args", [])):
                                continue
                            cs_ln = cs.get("lineno", 0)
                            cs_col = cs.get("col_offset", 0)
                            if (match_ln and cs_ln == match_ln
                                    and cs_col == match_col):
                                matched = cs
                                break
                            if not match_ln:
                                matched = cs
                        if matched:
                            arg_src = matched["args"][param_idx]
                            arg_src = normalize_source(arg_src)
                            if isinstance(arg_src, CallResult):
                                top = self._top_source(
                                    module, arg_src.callee, tracers)
                                if top and top not in ("local", "python",
                                                       "unknown", ""):
                                    return top
                            if isinstance(arg_src, str):
                                top = self._top_source(module, arg_src, tracers)
                                if top and top not in ("local", "python",
                                                       "unknown", ""):
                                    return top
        return None

    ## Get the constructor call-site position for a receiver instance.
    #  @param receiver The variable name bound to a class instance.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @return Tuple of (lineno, col_offset) or (0, 0) if unknown.
    def _receiver_ctor_pos(self, receiver, tracer):
        if not receiver or not isinstance(receiver, str):
            return (0, 0)
        sd = tracer.symbols.direct.get(receiver)
        sd = normalize_source(sd)
        if isinstance(sd, CallResult):
            return (sd.call_lineno, sd.call_col_offset)
        return (0, 0)

    ## Resolve a parameter name to its call-site argument for a specific callee.
    #
    #  Unlike _trace_parameter_source, this only searches the given callee's
    #  call-sites, preventing false positives from same-named parameters in
    #  other functions.
    ## Look up the return source of a local function via call-graph facts.
    #
    #  Searches the current module's ModuleCallGraph first, then falls back
    #  to all modules (for cross-file imported local functions).  Returns a
    #  single source only when unambiguous; SourceSet with multiple
    #  import-backed sources is left for the classifier (7B-full PR2).
    #  @param cur_module The module where the call occurs.
    #  @param callee Bare function name or qualname (e.g. "make_array").
    #  @return A non-local source string, or None.
    def _lookup_cg_return_source(self, cur_module, callee):
        if not isinstance(callee, str):
            return None
        cg = getattr(self, 'project_cg', None)
        if cg is None:
            return None
        # Search current module first.  Only fall back to other modules
        # when the function is NOT found locally (cross-file import case).
        search_modules = list(cg.modules.keys())
        if cur_module and cur_module in search_modules:
            search_modules.remove(cur_module)
            search_modules.insert(0, cur_module)
        for module in search_modules:
            mcg = cg.modules.get(module)
            if mcg is None:
                continue
            fs = mcg.functions.get(callee)
            if fs is None:
                continue
            # Found in this module — if no returns, don't fall back to others.
            if fs.returns is None:
                return None
            # Tuple return summaries require caller-side positional binding;
            # they are not whole-result sources for the legacy resolver.
            if self._is_tuple_return_source(fs.returns):
                return None
            returns_norm = normalize_source(fs.returns)
            if isinstance(returns_norm, SourceSet):
                # Collect import-backed tops; return single if unambiguous.
                tops = []
                for src in returns_norm.sources:
                    src_norm = normalize_source(src)
                    if isinstance(src_norm, str) and not self.is_local(src_norm):
                        top = self._top_name(src_norm)
                        if top and top not in ("local", "unknown", ""):
                            tops.append(top)
                    elif isinstance(src_norm, InstanceMethod) and isinstance(src_norm.receiver, str):
                        top = self._top_name(src_norm.receiver)
                        if top and top not in ("local", "unknown", ""):
                            tops.append(top)
                    elif isinstance(src_norm, CallResult) and isinstance(src_norm.callee, str):
                        top = self._top_name(src_norm.callee)
                        if top and top not in ("local", "unknown", ""):
                            tops.append(top)
                if len(tops) == 1:
                    return tops[0]
                # Multiple or zero import-backed sources — let classifier handle.
                continue
            if isinstance(returns_norm, str) and not self.is_local(returns_norm):
                top = self._top_name(returns_norm)
                if top and top not in ("local", "unknown", ""):
                    return top
            elif isinstance(returns_norm, CallResult):
                if isinstance(returns_norm.callee, str):
                    top = self._top_name(returns_norm.callee)
                    if top and top not in ("local", "unknown", ""):
                        return top
        return None

    # _is_container_receiver and _lookup_cg_edge_arg_source removed
    # (1.0.5 P0 cleanup).  Arg-source evidence belongs in
    # SymbolProvenance, not ApiCall.top_library.

    ## Look up import-backed constructor attr used by a specific method (7B-full PR3).
    #
    #  Searches ProjectCallGraph for edges where the method (identified by
    #  class_name + method_name) calls through a self.attr whose constructor
    #  source is import-backed.  Only attrs actually used by the method are
    #  considered — a class's unrelated import-backed attrs do not leak.
    #  @param cur_module The module where the class is defined.
    #  @param class_name The local class name.
    #  @param method_name The method being called (e.g. "fit").
    #  @return Tuple of (src_module, top_library) or None.
    def _lookup_cg_class_attr_source(self, cur_module, class_name, method_name):
        if not isinstance(class_name, str) or not isinstance(method_name, str):
            return None
        cg = getattr(self, 'project_cg', None)
        if cg is None:
            return None
        # Search current module first, then all modules.
        search_modules = list(cg.modules.keys())
        if cur_module and cur_module in search_modules:
            search_modules.remove(cur_module)
            search_modules.insert(0, cur_module)
        for module in search_modules:
            mcg = cg.modules.get(module)
            if mcg is None:
                continue
            cs = mcg.classes.get(class_name)
            if cs is None:
                continue
            # Collect import-backed attrs with their library provenance.
            import_attrs = {}  # attr_name -> (src_module, top)
            for attr_name, src in cs.attrs.items():
                src_norm = normalize_source(src)
                if isinstance(src_norm, CallResult):
                    if isinstance(src_norm.callee, str):
                        callee = src_norm.callee
                        if _is_builtin(callee) or self.is_local(callee):
                            continue
                        top = self._top_name(callee)
                        if top and top not in ("local", "unknown", ""):
                            import_attrs[attr_name] = (module, top)
                elif isinstance(src_norm, str):
                    if (self.is_local(src_norm) or src_norm in ("local", "unknown", "")
                            or _is_builtin(src_norm)):
                        continue
                    bare = attr_name[5:] if attr_name.startswith("self.") else attr_name
                    if src_norm == bare or src_norm.startswith(bare):
                        continue
                    if '.' not in src_norm:
                        continue
                    top = self._top_name(src_norm)
                    if top and top not in ("local", "unknown", ""):
                        import_attrs[attr_name] = (module, top)
            if not import_attrs:
                return None
            # Only return an attr if the method actually uses it.
            # Check edges where caller is this method.
            method_qualname = class_name + "." + method_name
            method_tops = {}  # top -> (src_module, top)
            for edge in mcg.edges:
                if edge.caller.qualname != method_qualname:
                    continue
                rcvr = edge.receiver_source
                if rcvr is None:
                    continue
                rcvr_norm = normalize_source(rcvr)
                # Match receiver against import-backed attrs.
                for attr_name, (attr_mod, attr_top) in import_attrs.items():
                    if self._edge_receiver_matches_attr(rcvr_norm, cs, attr_name):
                        method_tops[attr_top] = (attr_mod, attr_top)
            if len(method_tops) == 1:
                return list(method_tops.values())[0]
            # Multiple candidates — return None, let classifier handle alternatives.
            return None
        return None

    ## Check whether a CallEdge receiver matches a ClassSummary attr source.
    #  @param rcvr_norm Normalized receiver source from the edge.
    #  @param cs The ClassSummary.
    #  @param attr_name The attr name to check (e.g. "self.gp").
    #  @return True if the receiver matches the attr's source.
    def _edge_receiver_matches_attr(self, rcvr_norm, cs, attr_name):
        attr_src = cs.attrs.get(attr_name)
        if attr_src is None:
            return False
        attr_norm = normalize_source(attr_src)
        if isinstance(rcvr_norm, CallResult) and isinstance(attr_norm, CallResult):
            return rcvr_norm.callee == attr_norm.callee
        if isinstance(rcvr_norm, str) and isinstance(attr_norm, str):
            return rcvr_norm == attr_norm
        return rcvr_norm == attr_norm

    #  @param module The module where the call occurs.
    #  @param callee The function name whose parameter is being resolved.
    #  @param param_name The parameter name to resolve.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return A source value from the call-site argument, or None.
    def _resolve_param_to_arg(self, module, callee, param_name, tracers,
                               call_lineno=0, call_col_offset=0):
        tr = tracers.get(module)
        if not tr or not isinstance(param_name, str):
            return None
        params = tr.function_params.get(callee, [])
        if param_name not in params:
            return None
        param_idx = params.index(param_name)
        best = None
        for call_site in tr.call_sites.get(callee, []):
            if param_idx >= len(call_site["args"]):
                continue
            best = call_site["args"][param_idx]
            if call_lineno:
                cs_lineno = call_site.get("lineno", 0)
                cs_col = call_site.get("col_offset", 0)
                if cs_lineno == call_lineno and cs_col == call_col_offset:
                    return best
        return best

    ## Recursively trace a symbol through cross-file imports to its origin.
    #
    #  Follows direct sources across module boundaries, handling
    #  structured sources (container items, instance methods, container iters,
    #  call results) at each step.
    #  @param module The current module being traced from.
    #  @param symbol The symbol to trace.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param visited Set of already-visited (module, symbol) pairs.
    #  @return Ordered chain list from symbol to origin.
    # ── trace engine ─────────────────────────────────────────────────────

    def trace_symbol(self, module, symbol, tracers, visited,
                     _direct_source=None):
        if (module, symbol) in visited:
            return []
        visited.add((module, symbol))
        tracer = tracers.get(module)
        if not tracer:
            return []
        direct_source = (
            _direct_source if _direct_source is not None
            else tracer.symbols.direct.get(symbol))
        if not direct_source:
            return self._trace_unbound_symbol(
                module, symbol, tracer, tracers, visited)

        parameter_chain = self._trace_direct_parameter_chain(
            module, symbol, direct_source, tracer, tracers, visited)
        if parameter_chain is not None:
            return parameter_chain
        structured = self._resolve_structured_source(
            module, direct_source, tracers, _seen=set(visited))
        if structured is not None:
            return self._trace_structured_chain(
                module, symbol, direct_source, structured,
                tracers, visited)
        if isinstance(direct_source, tuple):
            return [symbol, str(direct_source)]
        return self._trace_plain_source(
            module, symbol, direct_source, tracer, tracers, visited)

    ## Trace an unresolved name through prefixes and wildcard imports.
    def _trace_unbound_symbol(self, module, symbol, tracer,
                              tracers, visited):
        if isinstance(symbol, str) and "." in symbol:
            prefix = symbol.split(".")[0]
            if prefix in tracer.symbols.direct:
                sub_chain = self.trace_symbol(
                    module, prefix, tracers, visited)
                if sub_chain:
                    return [symbol] + sub_chain
        if (isinstance(symbol, str)
                and "." in symbol
                and self._has_import_origin(tracer, symbol)):
            full_symbol = self.module_mapper.resolve_module_name(
                symbol, module)
            if not self.is_local(full_symbol):
                return [symbol]
        wildcard_chain = self._trace_wildcard_symbol(
            symbol, tracer, tracers, visited)
        if wildcard_chain is not _NO_TRACE_CHAIN:
            return wildcard_chain
        if (symbol == "self"
                or (isinstance(symbol, str)
                    and symbol.startswith("self."))):
            return [symbol, "local"]
        if isinstance(symbol, str) and _is_builtin(symbol):
            return [symbol, "python"]
        return [symbol]

    ## Trace one unresolved name through wildcard-import candidates.
    #  @return Chain or the module sentinel when no wildcard applies.
    def _trace_wildcard_symbol(self, symbol, tracer, tracers, visited):
        if not tracer.wildcard_modules:
            return _NO_TRACE_CHAIN
        tops = []
        local_modules = []
        for wildcard_module in tracer.wildcard_modules:
            actual_module = self._resolved_wildcard_module(
                wildcard_module, tracers)
            if self.is_local(actual_module):
                local_modules.append(actual_module)
                continue
            top = wildcard_module.split(".")[0]
            if top not in tops:
                tops.append(top)
        if tops:
            if len(tops) == 1:
                return [symbol, tops[0]]
            return [symbol, "[" + ",".join(tops) + "]"]
        for actual_module in local_modules:
            src_tracer = tracers.get(actual_module)
            if src_tracer and symbol in src_tracer.symbols.direct:
                sub_chain = self.trace_symbol(
                    actual_module, symbol, tracers, visited)
                if sub_chain:
                    return [symbol] + sub_chain
        if local_modules:
            return [symbol, "local"]
        return _NO_TRACE_CHAIN

    ## Resolve a wildcard import name to a known project module when possible.
    def _resolved_wildcard_module(self, wildcard_module, tracers):
        if wildcard_module in tracers:
            return wildcard_module
        for module in tracers:
            if (module == wildcard_module
                    or module.endswith("." + wildcard_module)):
                return module
        return wildcard_module

    ## Trace parameter evidence attached to one direct binding.
    #  @return A chain, or None when parameter evidence does not apply.
    def _trace_direct_parameter_chain(
            self, module, symbol, direct_source, tracer, tracers, visited):
        if direct_source == "local":
            chain = self._trace_parameter_source(
                module, symbol, symbol, tracer, tracers, visited)
            if chain:
                return chain
        if isinstance(direct_source, str) and direct_source != symbol:
            chain = self._trace_parameter_source(
                module, direct_source, symbol, tracer, tracers, visited)
            if chain:
                return chain
        return None

    ## Continue a chain from a normalized structured source.
    def _trace_structured_chain(self, module, symbol, direct_source,
                                structured, tracers, visited):
        display_name, src_module, src_symbol = structured
        sub_chain = self.trace_symbol(
            src_module, src_symbol, tracers, visited)
        if sub_chain and sub_chain != [src_symbol]:
            return [symbol, display_name] + sub_chain
        src_tracer = tracers.get(src_module)
        if (sub_chain == [src_symbol]
                and isinstance(src_symbol, str)
                and src_tracer is not None
                and self._has_import_origin(src_tracer, src_symbol)):
            return [symbol, display_name, src_symbol]
        if (isinstance(src_symbol, str)
                and ("." in src_symbol
                     or "[" in src_symbol
                     or src_symbol == "local"
                     or _is_builtin(src_symbol)
                     or src_symbol in ("unknown", "python"))):
            if "." in src_symbol:
                first = src_symbol.split(".")[0]
                full_first = self.module_mapper.resolve_module_name(
                    first, src_module)
                if self.is_local(full_first):
                    return [symbol, display_name, src_module]
            return [symbol, display_name, src_symbol]
        if (isinstance(direct_source, CallResult)
                and isinstance(
                    getattr(direct_source, "result_source", None), str)
                and src_symbol == getattr(
                    direct_source, "result_source", None)):
            return [symbol, display_name, src_symbol]
        return [symbol, display_name, src_module]

    ## Trace an ordinary string or opaque direct source.
    def _trace_plain_source(self, module, symbol, direct_source, tracer,
                            tracers, visited):
        if isinstance(direct_source, str):
            full_source = self.module_mapper.resolve_module_name(
                direct_source, module)
        else:
            full_source = direct_source
        if self.is_local(full_source):
            sub_chain = self.trace_symbol(
                full_source, symbol, tracers, visited)
            if sub_chain and sub_chain != [symbol]:
                return [symbol, full_source] + sub_chain
            return [symbol, full_source]
        if (isinstance(full_source, str)
                and full_source in tracer.symbols.direct):
            sub_chain = self.trace_symbol(
                module, full_source, tracers, visited)
            if sub_chain:
                return [symbol] + sub_chain
            return [symbol, full_source]
        return [symbol, full_source]

    ## Extract the top-level name from a dotted name string.
    #  @param name Possibly dotted name.
    #  @return The first component before a dot.
    def _top_name(self, name):
        if isinstance(name, str) and "." in name:
            return name.split(".")[0]
        return name

    ## Resolve a symbol to its top-level source library.
    #
    #  Traces through the chain and returns the top-level name, or "python"
    #  for builtins.
    #  @param src_module The module where the symbol is referenced.
    #  @param symbol The symbol to resolve.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return Top-level library name (e.g. "requests", "python").
    def _top_source(self, src_module, symbol, tracers, _seen=None):
        if not symbol:
            return None
        if isinstance(symbol, PythonShape):
            return "python"
        if isinstance(symbol, str) and _is_builtin(symbol):
            return "python"
        src_tracer = tracers.get(src_module)
        if src_tracer and self._is_known_local_symbol(src_tracer, symbol):
            return "local"
        visited = set(_seen) if _seen is not None else set()
        chain = self.trace_symbol(src_module, symbol, tracers, visited)
        if chain:
            top = self.extract_final_source(chain)
            if top in ("local", "python", "unknown", ""):
                return top
            if isinstance(symbol, str) and chain in ([symbol], [self._top_name(symbol)]):
                # Merged container candidates like "[requests,numpy]"
                # are not local/import-origin names — return as-is.
                if isinstance(symbol, str) and symbol.startswith("[") and symbol.endswith("]"):
                    return symbol
                if self.is_local(symbol):
                    return "local"
                if src_tracer and self._has_import_origin(src_tracer, symbol):
                    return self._top_name(symbol)
                # 1.0.5 P1: cross-file return tracing may resolve to a
                # library name imported in another module (e.g. flask
                # from factory tracing).  Only for simple names that
                # are clearly not local sub-modules.
                if isinstance(symbol, str) and '.' not in symbol:
                    all_mods = self.module_mapper.get_all_modules()
                    if not any(m.endswith('.' + symbol) for m in all_mods):
                        for _mt, mt_tracer in tracers.items():
                            if self._has_import_origin(mt_tracer, symbol):
                                return self._top_name(symbol)
                return "unknown"
            return top
        if src_tracer:
            top = src_tracer.symbols.get_top(symbol)
            if top:
                return self._top_name(top)
            if (isinstance(symbol, str)
                    and self._has_import_origin(src_tracer, symbol)):
                return self._top_name(symbol)
        return "unknown"

    ## Extract the ultimate source from a resolution chain.
    #
    #  Walks the chain in reverse; the first non-local, non-builtin element
    #  is the top-level library.
    #  @param chain The resolution chain list.
    #  @return Final source string.
    def extract_final_source(self, chain):
        if not chain:
            return ""
        found_local_module = False
        for item in reversed(chain):
            if isinstance(item, str) and _is_builtin(item):
                return "python"
            if isinstance(item, str) and not self.is_local(item):
                if found_local_module:
                    return "local"
                result = self._top_name(item)
                if result == "self":
                    return "local"
                return result
            if isinstance(item, str) and self.is_local(item):
                found_local_module = True
        return "local"
