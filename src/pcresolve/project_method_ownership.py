## @package pcresolve.project_method_ownership
#  Cross-file method ownership and parameter-receiver resolution.

from .builtin_ownership import _has_builtin_shape_method
from .container_resolution import _tuple_source_item
from .sources import (
    CallResult, ContainerItem, ContainerIter, DerivedResult,
    InstanceAttribute, InstanceMethod, ParameterSource, PythonShape,
    SourceSet, SuperMethod, UnknownSource, make_source_set,
    normalize_source, source_display,
)


_NO_METHOD_CANDIDATES = object()
_NO_STRUCTURED_SOURCE = object()


## Remove consecutive duplicate items while preserving order.
def _dedup_consecutive(chain):
    result = []
    for item in chain:
        if not result or item != result[-1]:
            result.append(item)
    return result


## Project method-ownership behavior mixed into ProjectAnalyzer.
class ProjectMethodOwnershipMixin:
    ## Resolve cross-file symbol references across all modules.
    #
    #  For each symbol in each module, trace its source through imports
    #  and assignments to find the final origin.
    #  @param module_tracers Dict of module_name -> SingleFileAnalyzer.
    def resolve_cross_file_symbols(self, module_tracers):
        self._call_searched_global = set()
        for module, tracer in module_tracers.items():
            self.global_symbols[module] = {}
            self.symbol_chains[module] = {}
            for symbol, direct_source in tracer.symbols.direct.items():
                chain = self.trace_symbol(module, symbol, module_tracers, set())
                if chain:
                    chain = _dedup_consecutive(chain)
                    self.global_symbols[module][symbol] = self.extract_final_source(chain)
                    self.symbol_chains[module][symbol] = chain
        self._call_searched_global = None


    ## Resolve a method call through class inheritance and cross-file imports.
    #
    #  Searches the class's method list, then recursively checks parent classes,
    #  following imports to other modules as needed.
    #  @param module The current module.
    #  @param class_symbol The class name.
    #  @param method_name The method being called.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param visited Set of already-visited (module, class, method) keys.
    #  @return (src_module, src_symbol) tuple, or None.
    def _resolve_method_symbol(self, module, class_symbol, method_name, tracers, visited):
        tracer = tracers.get(module)
        if not tracer:
            return None
        key = (module, class_symbol, method_name)
        if key in visited:
            return None
        visited.add(key)
        methods = tracer.class_methods.get(class_symbol, [])
        if method_name in methods:
            return (module, method_name)
        for base_symbol in tracer.class_bases.get(class_symbol, []):
            if base_symbol in tracer.class_methods:
                resolved = self._resolve_method_symbol(module, base_symbol, method_name, tracers, visited)
                if resolved:
                    return resolved
            base_direct = normalize_source(tracer.symbols.direct.get(base_symbol))
            if isinstance(base_direct, CallResult):
                base_direct = base_direct.callee
                if base_direct == base_symbol:
                    base_direct = tracer.import_from_symbols.get(base_symbol, base_direct)
            if isinstance(base_direct, str):
                if self.is_local(base_direct):
                    src_module = base_direct
                    resolved = self._resolve_method_symbol(src_module, base_symbol, method_name, tracers, visited)
                    if resolved:
                        return resolved
                else:
                    return (module, base_symbol)
            # P0: handle external base classes not in symbols.direct.
            # When a local class inherits from tornado.tcpserver.TCPServer
            # and the base_symbol dotted name isn't stored as a symbol,
            # check whether the top-level prefix is an import.
            if (isinstance(base_symbol, str) and '.' in base_symbol
                    and not base_direct):
                prefix = base_symbol.split('.')[0]
                aliases = getattr(tracer, "import_aliases", set())
                alias_prefixes = {
                    a.split('.')[0] for a in aliases if isinstance(a, str)}
                alias_prefixes |= {
                    a.split('.')[0] for a in getattr(
                        tracer, "import_from_symbols", {}) if isinstance(a, str)}
                if prefix in alias_prefixes:
                    return (module, prefix)
        class_direct = normalize_source(tracer.symbols.direct.get(class_symbol))
        if isinstance(class_direct, CallResult):
            class_direct = class_direct.callee
            if class_direct == class_symbol:
                class_direct = tracer.import_from_symbols.get(class_symbol, class_direct)
        if isinstance(class_direct, str):
            if self.is_local(class_direct):
                src_module = class_direct
                resolved = self._resolve_method_symbol(src_module, class_symbol, method_name, tracers, visited)
                if resolved:
                    return resolved
            else:
                if class_direct == "local":
                    rs = tracer.return_sources.get(class_symbol)
                    if rs is not None and isinstance(rs, tuple) and len(rs) == 3 and rs[0] == "call_result":
                        return (module, rs[1])
                return (module, class_symbol)
        return None

    ## Trace a function or constructor parameter through collected call sites.
    #  @param module Module containing the parameter.
    #  @param param_name Parameter name to resolve.
    #  @param display_symbol Symbol to use at the start of the returned chain.
    #  @param tracer Single-file analyzer for module.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param visited Set of visited trace keys.
    #  @return Chain from display_symbol to argument origin, or None.
    def _trace_parameter_source(self, module, param_name, display_symbol, tracer, tracers, visited):
        for func_name, params in tracer.function_params.items():
            try:
                param_idx = params.index(param_name)
            except ValueError:
                continue
            for call_site in tracer.call_sites.get(func_name, []):
                if param_idx >= len(call_site["args"]):
                    continue
                arg_src = call_site["args"][param_idx]
                if isinstance(arg_src, str):
                    sub_chain = self.trace_symbol(
                        call_site["module"], arg_src, tracers, visited
                    )
                elif arg_src is not None:
                    sub_chain = self.trace_symbol(
                        call_site["module"], param_name, tracers, set(),
                        _direct_source=arg_src,
                    )
                else:
                    sub_chain = None
                if sub_chain:
                    if sub_chain[0] == display_symbol:
                        return sub_chain
                    return [display_symbol] + sub_chain
        return None

    ## Resolve a structured (tuple) source to its concrete origin.
    #
    #  Handles the four structured tuple kinds:
    #  - "container_item" for subscript access
    #  - "instance_method" for method calls
    #  - "container_iter" for iteration over containers
    #  - "call_result" for function call return values
    #  @param module The current module.
    #  @param direct_source The structured tuple (kind, arg1, arg2).
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (display_name, src_module, src_symbol) tuple, or None.

    ## Resolve a SourceSet to a primary top library using origin-aware rules.
    #
    #  Delegates to SourceSetResolver.  See source_resolution.py for the
    #  origin-aware convergence rules (dict_lookup, return, default).
    def _resolve_sourceset_primary(self, module, sourceset, tracers, _seen=None):
        return self._source_resolver.resolve_primary(
            module, sourceset, tracers, _seen=_seen)

    # ── structured source resolution ─────────────────────────────────────

    def _resolve_structured_source(self, module, direct_source, tracers,
                                   _seen=None):
        if _seen is None:
            _seen = set()
        direct_source = normalize_source(direct_source)
        structured_key = (
            "structured", module, type(direct_source).__name__,
            source_display(direct_source),
        )
        if structured_key in _seen:
            return (source_display(direct_source), module, "unknown")
        seen = set(_seen)
        seen.add(structured_key)
        resolved = self._resolve_direct_structured_owner(
            module, direct_source, tracers, seen)
        if resolved is not _NO_STRUCTURED_SOURCE:
            return resolved
        parts = self._structured_source_parts(direct_source)
        if parts is None:
            return None
        kind, first, second, callee_display = parts
        if kind == "container_item":
            return self._resolve_container_item_source(
                module, first, second, tracers, seen)
        if kind == "instance_method":
            return self._resolve_instance_method_source(
                module, direct_source, first, second, tracers, seen)
        if kind == "super_method":
            return self._resolve_super_method_source(
                module, first, second, tracers, seen)
        if kind == "container_iter":
            return self._resolve_container_iter_source(
                module, first, tracers)
        if kind == "call_result":
            return self._resolve_call_result_source(
                module, direct_source, first, callee_display,
                tracers, seen)
        return None

    ## Resolve structured values that already carry direct owner evidence.
    #  @return Resolution tuple or the module sentinel when dispatch continues.
    def _resolve_direct_structured_owner(
            self, module, direct_source, tracers, seen):
        display = source_display(direct_source)
        if isinstance(direct_source, PythonShape):
            return (display, module, "python")
        if isinstance(direct_source, DerivedResult):
            candidates = self._origin_candidates(
                module, direct_source, tracers, _seen=set(seen))
            unique = self._dedupe_list([
                candidate for candidate in candidates
                if candidate not in (None, "")
            ])
            owner = unique[0] if len(unique) == 1 else "unknown"
            return (display, module, owner)
        if isinstance(direct_source, SourceSet):
            return self._resolve_structured_sourceset(
                module, direct_source, tracers, seen)
        if isinstance(direct_source, ParameterSource):
            owners = self._dedupe_list([
                owner for owner in self._argument_owner_candidates(
                    module, direct_source, tracers)
                if owner not in (None, "")
            ])
            owner = owners[0] if len(owners) == 1 else "unknown"
            return (display, module, owner)
        return _NO_STRUCTURED_SOURCE

    ## Resolve a SourceSet without selecting an unproven runtime branch.
    def _resolve_structured_sourceset(self, module, source, tracers, seen):
        display = source_display(source)
        primary = self._resolve_sourceset_primary(
            module, source, tracers, _seen=set(seen))
        if primary:
            return (display, module, primary)
        if source.origin in ("builtin_element", "function_branch"):
            return (display, module, "unknown")
        for item in source.sources:
            if isinstance(item, str):
                top = self._top_source(
                    module, item, tracers, _seen=set(seen))
                if top and top not in (
                        "local", "python", "unknown", ""):
                    return (display, module, item)
        for item in source.sources:
            if isinstance(item, str):
                return (display, module, item)
        return None

    ## Normalize one structured source into its dispatch components.
    def _structured_source_parts(self, source):
        if isinstance(source, ContainerItem):
            return ("container_item", source.container, source.index, None)
        if isinstance(source, ContainerIter):
            return ("container_iter", source.container, "*", None)
        if isinstance(source, InstanceMethod):
            return ("instance_method", source.receiver, source.method, None)
        if isinstance(source, SuperMethod):
            return ("super_method", source.class_key, source.method, None)
        if isinstance(source, CallResult):
            display = source.display_name or source.callee
            return ("call_result", source.callee, None, display)
        if isinstance(source, tuple) and len(source) == 3:
            kind, first, second = source
            return (kind, first, second, None)
        return None

    ## Resolve super().method() through local and imported base classes.
    def _resolve_super_method_source(
            self, module, class_key, method, tracers, seen):
        tracer = tracers.get(module)
        if not tracer:
            return None
        resolved_owners = []
        for base_symbol in tracer.class_bases.get(class_key, []):
            if (base_symbol in tracer.class_methods
                    and method in tracer.class_methods[base_symbol]):
                resolved_owners.append("local")
                continue
            base_direct = normalize_source(
                tracer.symbols.direct.get(base_symbol))
            if isinstance(base_direct, CallResult):
                base_direct = base_direct.callee
            if (isinstance(base_direct, str)
                    and base_direct not in (
                        "local", "python", "unknown", "")):
                top = self._top_source(
                    module, base_direct, tracers, _seen=set(seen))
                if top and top not in (
                        "local", "python", "unknown", ""):
                    resolved_owners.append(top)
                    continue
            if isinstance(base_symbol, str) and "." in base_symbol:
                top = self._top_source(
                    module, base_symbol, tracers, _seen=set(seen))
                if top and top not in (
                        "local", "python", "unknown", ""):
                    resolved_owners.append(top)
                    continue
        unique = list(dict.fromkeys(resolved_owners))
        if len(unique) == 1:
            return ("super()." + method, module, unique[0])
        if len(unique) > 1:
            return ("super()." + method, module, "unknown")
        return ("super()." + method, module, "local")

    ## Resolve a method receiver from all known parameter evidence.
    #
    #  A function parameter is not evidence of project-local ownership. A
    #  unique owner is returned only when call sites, static callbacks, or
    #  parameterization values converge. Uncalled and conflicting parameters
    #  remain unknown.
    #
    #  @param module Module containing the function parameter.
    #  @param method_source Parameter-backed InstanceMethod source.
    #  @param tracer Single-file analyzer for module.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Structured-source recursion guard.
    #  @return Converged owner string or "unknown".
    def _resolve_parameter_method_top(self, module, method_source,
                                      tracer, tracers, _seen=None):
        parameter = method_source.parameter_name
        scope_name = method_source.parameter_scope
        if not parameter or not scope_name:
            return "unknown"

        receiver = method_source.receiver
        if (not isinstance(receiver, str)
                or not (receiver == parameter
                        or receiver.startswith(parameter + "."))):
            return "unknown"

        params = tracer.function_params.get(scope_name)
        if params is None:
            params = tracer.function_params.get(
                scope_name.rsplit(".", 1)[-1], [])
        if parameter not in params:
            return "unknown"

        param_index = params.index(parameter)
        call_arguments = self._parameter_call_arguments(
            module, scope_name, parameter, param_index, tracer, tracers,
            prefer_protocol_shape=True)
        if not call_arguments:
            return "unknown"

        receiver_class_filter = None
        scope_parts = scope_name.rsplit(".", 1)
        module_cg = getattr(self, "project_cg", None)
        defining_cg = (
            module_cg.modules.get(module)
            if module_cg is not None else None)
        if (len(scope_parts) == 2 and defining_cg is not None
                and scope_parts[0] in defining_cg.classes):
            receiver_class_filter = (module, scope_parts[0])

        attribute_path = (
            receiver[len(parameter) + 1:].split(".")
            if receiver != parameter else [])
        owners = []
        if not attribute_path:
            for arg_module, arg_source in call_arguments:
                if arg_source is None:
                    return "unknown"
                owners.extend(self._argument_method_owner_candidates(
                    arg_module, arg_source, method_source.method, tracers,
                    _seen=set(_seen or set()),
                    receiver_class_filter=receiver_class_filter))
        else:
            for arg_module, arg_source in call_arguments:
                if arg_source is None:
                    return "unknown"
                candidates = self._parameter_attribute_owner_candidates(
                    arg_module, arg_source, attribute_path, tracers)
                owners.extend(candidates)

        unique = self._dedupe_list([
            owner for owner in owners if owner not in (None, "")])
        if not unique or "unknown" in unique:
            return "unknown"
        if len(unique) == 1:
            return unique[0]
        return "unknown"

    ## Check whether an expression is composed only of direct parameters.
    #
    #  Subscript-derived parameters and local attributes are deliberately
    #  excluded. Their runtime element or attribute type is not established
    #  by the expression shape alone.
    #  @param source Source to inspect.
    #  @return True for a direct-parameter expression.
    def _is_direct_parameter_expression(self, source):
        source = normalize_source(source)
        if isinstance(source, ParameterSource):
            return not source.derived and not source.attributes
        if isinstance(source, DerivedResult):
            return (
                source.kind == "expression"
                and bool(source.sources)
                and all(self._is_direct_parameter_expression(item)
                        for item in source.sources)
            )
        return False

    ## Check whether every expression operand has bounded call-edge evidence.
    #  @param source Source or expression source to inspect.
    #  @return True for direct parameters and deferred instance fields.
    def _is_bounded_expression_source(self, source):
        source = normalize_source(source)
        if isinstance(source, InstanceAttribute):
            return True
        if isinstance(source, ParameterSource):
            return not source.derived and not source.attributes
        if isinstance(source, DerivedResult):
            return (
                source.kind == "expression"
                and bool(source.sources)
                and all(self._is_bounded_expression_source(item)
                        for item in source.sources)
            )
        return False

    ## Resolve a method on an expression derived from one or more parameters.
    #
    #  For example, ``combined = left + right`` followed by
    #  ``combined.reshape(...)`` carries two parameter sources.  Resolve each
    #  operand through its exact project call sites and accept the method
    #  owner only when every operand converges to the same owner.  This is a
    #  data-flow rule, not a library or method-name whitelist.
    #
    #  @param module Module containing the expression.
    #  @param source DerivedResult describing the expression operands.
    #  @param method Receiver method name.
    #  @param tracer Analyzer for the defining module.
    #  @param tracers Dict of module name to analyzer.
    #  @return One owner string, or "unknown" when the operands do not
    #  converge.
    def _resolve_derived_expression_method_top(self, module, source, method,
                                                tracer, tracers):
        external = self._resolve_expression_external_top(module, source, tracers)
        if external != "unknown":
            return external
        owners = []
        seen = set()

        def collect(value):
            value = normalize_source(value)
            if isinstance(value, DerivedResult):
                if value.kind != "expression" or not value.sources:
                    owners.append("unknown")
                    return
                for operand in value.sources:
                    collect(operand)
                return
            if isinstance(value, SourceSet):
                if not value.sources:
                    owners.append("unknown")
                    return
                for operand in value.sources:
                    collect(operand)
                return
            if isinstance(value, ParameterSource):
                key = (value.scope, value.name, method)
                if key in seen:
                    owners.append("unknown")
                    return
                seen.add(key)
                params = tracer.function_params.get(value.scope)
                if params is None:
                    params = tracer.function_params.get(
                        value.scope.rsplit(".", 1)[-1], [])
                if value.name not in params:
                    owners.append("unknown")
                    return
                arguments = self._parameter_call_arguments(
                    module, value.scope, value.name, params.index(value.name),
                    tracer, tracers, prefer_protocol_shape=True)
                if not arguments:
                    owners.append("unknown")
                    return
                for arg_module, arg_source in arguments:
                    candidates = self._argument_method_owner_candidates(
                        arg_module, arg_source, method, tracers)
                    owners.extend(candidates or ["unknown"])
                return
            candidates = self._argument_method_owner_candidates(
                module, value, method, tracers)
            owners.extend(candidates or ["unknown"])

        collect(source)
        unique = self._dedupe_list(
            owner for owner in owners if owner not in (None, ""))
        if len(unique) == 1 and unique[0] != "unknown":
            return unique[0]
        return "unknown"

    ## Resolve an expression receiver from converged import-backed operands.
    #
    #  This handles expressions that combine direct parameters with an
    #  independently resolved import-backed result.  The ordinary origin
    #  resolver follows parameter call edges and requires every operand to
    #  converge.  Python, local, unresolved, and conflicting candidates are
    #  deliberately rejected here because they do not prove one external
    #  receiver owner.
    #  @param module Module containing the expression.
    #  @param source DerivedResult describing the expression operands.
    #  @param tracers Dict of module name to analyzer.
    #  @return One import-backed owner string, or "unknown".
    def _resolve_expression_external_top(self, module, source, tracers):
        source = normalize_source(source)
        if (not isinstance(source, DerivedResult)
                or source.kind != "expression"
                or not source.sources):
            return "unknown"
        candidates = self._dedupe_list(
            self._origin_candidates(module, source, tracers))
        if (len(candidates) == 1
                and candidates[0] not in (
                    None, "", "local", "python", "unknown")):
            return candidates[0]
        return "unknown"

    ## Check whether an expression retains independent owner evidence.
    #
    #  When such evidence conflicts with parameter flow, the receiver must
    #  remain unknown instead of falling back to local.  Expressions made
    #  only from local and parameter sources retain the existing local
    #  identity contract.
    #  @param source Expression source to inspect.
    #  @return True when an operand carries non-local owner evidence.
    def _has_expression_owner_evidence(self, source):
        source = normalize_source(source)
        if isinstance(source, (CallResult, PythonShape)):
            return True
        if isinstance(source, SourceSet):
            return any(self._has_expression_owner_evidence(item)
                       for item in source.sources)
        if isinstance(source, DerivedResult):
            return any(self._has_expression_owner_evidence(item)
                       for item in source.sources)
        if isinstance(source, str):
            return source not in ("", "local", "python", "unknown")
        return False

    ## Resolve argument ownership for one concrete receiver method.
    #
    #  PythonShape values must support the requested builtin protocol.
    #  Forwarded parameters are followed recursively; all other sources use
    #  ordinary owner resolution.
    #  @param module Module containing the argument expression.
    #  @param source Argument source.
    #  @param method Receiver method name.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Parameter recursion guard.
    #  @param receiver_class_filter Optional project-local virtual-dispatch
    #  class context retained while following forwarded parameters.
    #  @param _context Exact local return context, before owner projection.
    #  @return Candidate owner strings.
    def _argument_method_owner_candidates(
            self, module, source, method, tracers, _seen=None,
            receiver_class_filter=None, _context=None):
        source = normalize_source(source)
        if isinstance(source, SourceSet):
            candidates = []
            for item in source.sources:
                candidates.extend(self._argument_method_owner_candidates(
                    module, item, method, tracers, _seen,
                    receiver_class_filter, _context))
            return self._dedupe_list(candidates) or ["unknown"]
        if isinstance(source, CallResult):
            candidates = self._call_result_method_owner_candidates(
                module, source, method, tracers, _seen,
                receiver_class_filter, _context)
            if candidates is not _NO_METHOD_CANDIDATES:
                return candidates
        if isinstance(source, ParameterSource):
            candidates = self._context_parameter_method_owner_candidates(
                module, source, method, tracers, _seen,
                receiver_class_filter, _context)
            if candidates is not _NO_METHOD_CANDIDATES:
                return candidates
        if isinstance(source, (ContainerIter, ContainerItem)):
            seen = set(_seen or set())
            key = ("container-method", module, type(source).__name__,
                   source_display(source), method, receiver_class_filter)
            if key in seen:
                return ["unknown"]
            seen.add(key)
            _seen = seen
        if isinstance(source, InstanceAttribute):
            return [self._resolve_instance_attribute_method_top(
                module, source, method, tracers,
                _seen=set(_seen or set()))]
        if isinstance(source, PythonShape):
            return (["python"]
                    if _has_builtin_shape_method(source.kind, method)
                    else ["unknown"])
        if isinstance(source, InstanceMethod):
            candidates = self._instance_method_result_candidates(
                module, source, method, tracers, _seen,
                receiver_class_filter, _context)
            if candidates is not _NO_METHOD_CANDIDATES:
                return candidates
        if isinstance(source, DerivedResult):
            return self._derived_method_owner_candidates(
                module, source, method, tracers, _seen,
                receiver_class_filter, _context)
        if isinstance(source, ContainerIter):
            return self._iter_method_owner_candidates(
                module, source, method, tracers, _seen,
                receiver_class_filter, _context)
        if isinstance(source, ContainerItem):
            return self._item_method_owner_candidates(
                module, source, method, tracers, _seen,
                receiver_class_filter, _context)
        if not isinstance(source, ParameterSource):
            return self._origin_candidates(
                module, source, tracers,
                _seen=set(_seen or set()))
        return self._parameter_method_owner_candidates(
            module, source, method, tracers, _seen,
            receiver_class_filter, _context)

    ## Resolve method ownership carried by one call result.
    #  @return Candidates or the module sentinel when resolution falls through.
    def _call_result_method_owner_candidates(
            self, module, source, method, tracers, seen,
            receiver_class_filter, context):
        shape = self._returned_python_shape(module, source, tracers, context)
        if shape is not None:
            return self._argument_method_owner_candidates(
                module, shape, method, tracers, seen,
                receiver_class_filter, context)
        candidates = self._bounded_call_result_method_candidates(
            module, source, method, tracers, context, seen,
            receiver_class_filter)
        if candidates is not None:
            return candidates
        if isinstance(source.result_source, (
                PythonShape, SourceSet, CallResult, InstanceMethod,
                DerivedResult)):
            return self._argument_method_owner_candidates(
                source.source_module or module, source.result_source,
                method, tracers, seen, receiver_class_filter, context)
        return _NO_METHOD_CANDIDATES

    ## Resolve a parameter against an exact parent-linked call context.
    #  @return Candidates or the module sentinel when no context matches.
    def _context_parameter_method_owner_candidates(
            self, module, source, method, tracers, seen,
            receiver_class_filter, context):
        if source.derived:
            shape = self._returned_python_shape(
                module, source, tracers, context)
            if shape is not None:
                return self._argument_method_owner_candidates(
                    module, shape, method, tracers, seen,
                    receiver_class_filter, context)
        if context is None:
            return _NO_METHOD_CANDIDATES
        current = context
        while current is not None:
            if (module == current.target.module
                    and source.scope == current.target.qualname):
                if source.attributes or source.derived:
                    owners = self._bounded_source_candidates(
                        module, source, context, tracers,
                        set(seen or set()))
                    if owners and all(owner not in (
                            None, "", "local", "python", "unknown")
                            for owner in owners):
                        return owners
                    return ["unknown"]
                summary = self.project_cg.modules[
                    module].functions[current.target.qualname]
                if source.name not in summary.params:
                    return ["unknown"]
                arguments = self._edge_parameter_sources(
                    current.edge, summary, source.name,
                    summary.params.index(source.name),
                    prefer_protocol_shape=True)
                candidates = []
                for argument in arguments or [UnknownSource()]:
                    candidates.extend(self._argument_method_owner_candidates(
                        current.caller_module, argument, method, tracers,
                        seen, receiver_class_filter, current.parent))
                return self._dedupe_list(candidates) or ["unknown"]
            current = current.parent
        return _NO_METHOD_CANDIDATES

    ## Resolve the Python shape returned by an InstanceMethod source.
    #  @return Candidates or the module sentinel when no shape is proven.
    def _instance_method_result_candidates(
            self, module, source, method, tracers, seen,
            receiver_class_filter, context):
        result_shape = self._returned_python_shape(
            module, source, tracers, context)
        if result_shape is not None:
            return self._argument_method_owner_candidates(
                module, result_shape, method, tracers, seen,
                receiver_class_filter, context)
        receiver = source.receiver
        if source.parameter_scope and receiver == source.parameter_name:
            receiver = ParameterSource(
                source.parameter_scope, source.parameter_name)
        if self._returned_python_shape(
                module, receiver, tracers, context) is not None:
            return ["unknown"]
        return _NO_METHOD_CANDIDATES

    ## Resolve a derived expression used as a method receiver.
    def _derived_method_owner_candidates(
            self, module, source, method, tracers, seen,
            receiver_class_filter, context):
        if source.kind == "tuple":
            return self._argument_method_owner_candidates(
                module, PythonShape("tuple"), method, tracers, seen,
                receiver_class_filter, context)
        if self._is_bounded_expression_source(source):
            candidates = []
            for operand in source.sources:
                candidates.extend(self._argument_method_owner_candidates(
                    module, operand, method, tracers, seen,
                    receiver_class_filter=receiver_class_filter,
                    _context=context))
            unique = self._dedupe_list(candidates)
            if len(unique) == 1 and unique[0] != "unknown":
                return unique
        external = self._resolve_expression_external_top(
            module, source, tracers)
        if external != "unknown":
            return [external]
        return ["unknown"]

    ## Resolve an iterated value used as a method receiver.
    def _iter_method_owner_candidates(
            self, module, source, method, tracers, seen,
            receiver_class_filter, context):
        elements = self._returned_element_sources(
            module, source.container, tracers, iterable=True, _seen=seen)
        if elements is not None:
            candidates = []
            for origin, element in elements:
                candidates.extend(self._argument_method_owner_candidates(
                    origin, element, method, tracers, seen,
                    receiver_class_filter=receiver_class_filter,
                    _context=context))
            return self._dedupe_list(candidates) or ["unknown"]
        resolved = self._resolve_container_iter(
            module, source.container, tracers)
        if resolved is None:
            return ["unknown"]
        source_module, element_sources = resolved
        candidates = []
        for element_source in element_sources:
            candidates.extend(self._argument_method_owner_candidates(
                source_module, element_source, method, tracers, seen,
                receiver_class_filter=receiver_class_filter,
                _context=context))
        return self._dedupe_list(candidates) or ["unknown"]

    ## Resolve one selected container item used as a method receiver.
    def _item_method_owner_candidates(
            self, module, source, method, tracers, seen,
            receiver_class_filter, context):
        container = normalize_source(source.container)
        if isinstance(container, PythonShape):
            item_kind = container.item_kind
            if container.kind in ("str", "bytes"):
                item_kind = "str" if container.kind == "str" else "int"
            if item_kind:
                return self._argument_method_owner_candidates(
                    module, PythonShape(item_kind), method, tracers, seen,
                    receiver_class_filter=receiver_class_filter,
                    _context=context)
            return ["unknown"]
        selected = _tuple_source_item(container, source.index)
        if selected is not None:
            return self._argument_method_owner_candidates(
                module, selected, method, tracers, seen,
                receiver_class_filter=receiver_class_filter,
                _context=context)
        if isinstance(container, CallResult):
            candidates = self._bounded_call_result_item_candidates(
                module, container, source.index, tracers, _seen=seen)
            if candidates is not None:
                return candidates
        if isinstance(container, ParameterSource):
            return self._parameter_item_method_owner_candidates(
                module, container, source.index, method, tracers, seen,
                receiver_class_filter, context)
        resolved = self._resolve_container_item(
            module, source.container, source.index, tracers)
        if resolved is None:
            return ["unknown"]
        item_module, item_source = resolved
        return self._argument_method_owner_candidates(
            item_module, item_source, method, tracers, seen,
            receiver_class_filter=receiver_class_filter,
            _context=context)

    ## Resolve an item selected from a parameter or variadic pack.
    def _parameter_item_method_owner_candidates(
            self, module, container, index, method, tracers, seen,
            receiver_class_filter, context):
        item_key = ("item-method", module, container.scope,
                    container.name, index, method)
        item_seen = set(seen or set())
        if item_key in item_seen:
            return ["unknown"]
        item_seen.add(item_key)
        tracer = tracers.get(module)
        if tracer is None:
            return ["unknown"]
        params = tracer.function_params.get(container.scope)
        if params is None:
            params = tracer.function_params.get(
                container.scope.rsplit(".", 1)[-1], [])
        if container.name not in params:
            return ["unknown"]
        target_module_cg = self.project_cg.modules.get(module)
        summary = (target_module_cg.functions.get(container.scope)
                   if target_module_cg is not None else None)
        is_variadic = (
            summary is not None
            and container.name in (
                getattr(summary, "vararg", ""),
                getattr(summary, "kwarg", "")))
        if is_variadic:
            arguments = self._parameter_pack_item_arguments(
                module, container, index, tracers)
            return self._method_candidates_from_arguments(
                arguments, method, tracers, item_seen,
                receiver_class_filter, context)
        arguments = self._parameter_call_arguments(
            module, container.scope, container.name,
            params.index(container.name), tracer, tracers,
            prefer_protocol_shape=True)
        if not arguments:
            return ["unknown"]
        candidates = []
        for arg_module, arg_source in arguments:
            selected = _tuple_source_item(arg_source, index)
            if selected is None:
                selected = ContainerItem(arg_source, index)
            candidates.extend(self._argument_method_owner_candidates(
                arg_module, selected, method, tracers, item_seen,
                receiver_class_filter=receiver_class_filter,
                _context=context))
        return self._dedupe_list(candidates) or ["unknown"]

    ## Resolve method owners from an ordered argument-source collection.
    def _method_candidates_from_arguments(
            self, arguments, method, tracers, seen,
            receiver_class_filter, context):
        if not arguments:
            return ["unknown"]
        candidates = []
        for arg_module, arg_source in arguments:
            candidates.extend(self._argument_method_owner_candidates(
                arg_module, arg_source, method, tracers, seen,
                receiver_class_filter=receiver_class_filter,
                _context=context))
        return self._dedupe_list(candidates) or ["unknown"]

    ## Resolve a terminal parameter across incoming project call edges.
    def _parameter_method_owner_candidates(
            self, module, source, method, tracers, seen,
            receiver_class_filter, context):
        if source.attributes:
            return ["unknown"]
        if source.derived and source.derived_operation != "slice":
            return ["unknown"]
        parameter_seen = set(seen or set())
        key = (
            module, source.scope, source.name, method,
            source.derived_operation, receiver_class_filter,
        )
        if key in parameter_seen:
            return []
        parameter_seen.add(key)
        tracer = tracers.get(module)
        if tracer is None:
            return ["unknown"]
        params = tracer.function_params.get(source.scope)
        if params is None:
            params = tracer.function_params.get(
                source.scope.rsplit(".", 1)[-1], [])
        if source.name not in params:
            return ["unknown"]
        arguments = self._parameter_call_arguments(
            module, source.scope, source.name,
            params.index(source.name), tracer, tracers,
            prefer_protocol_shape=True,
            receiver_class_filter=receiver_class_filter)
        if not arguments:
            return ["unknown"]
        candidates = []
        for arg_module, arg_source in arguments:
            if source.derived:
                arg_source = normalize_source(arg_source)
                if isinstance(arg_source, PythonShape):
                    if arg_source.kind not in (
                            "str", "bytes", "list", "tuple"):
                        candidates.append("unknown")
                        continue
                elif not isinstance(arg_source, ParameterSource):
                    candidates.append("unknown")
                    continue
            candidates.extend(self._argument_method_owner_candidates(
                arg_module, arg_source, method, tracers, parameter_seen,
                receiver_class_filter=receiver_class_filter,
                _context=context))
        return self._dedupe_list(candidates)

    ## Validate a local call result's method before projecting return owners.
    #  @param module Module containing the result-producing call.
    #  @param source CallResult with the exact call-site position.
    #  @param method Requested receiver method.
    #  @param tracers Per-module analyzers.
    #  @param parent Enclosing forwarding context.
    #  @param seen Recursion guard.
    #  @param receiver_class_filter Optional local receiver class context.
    #  @return Candidate owners, or None when no local call context exists.
    def _bounded_call_result_method_candidates(
            self, module, source, method, tracers, parent, seen,
            receiver_class_filter):
        module = source.source_module or module
        contexts = self._bounded_call_contexts(
            module, source.call_lineno, source.call_col_offset,
            tracers, parent=parent, callee_name=source.display_name)
        if not contexts:
            return None
        # A constructor edge targets __init__, whose return is not the
        # instance returned by the class call. Keep class-owner resolution.
        if any(context.target.qualname.endswith(".__init__")
               and context.edge.callee_name.rsplit(".", 1)[-1] != "__init__"
               for context in contexts):
            return None
        candidates = []
        for context in contexts:
            key = ("return-method", module, source.call_lineno,
                   source.call_col_offset, context.target, method)
            if key in (seen or set()):
                candidates.append("unknown")
                continue
            context_seen = set(seen or set())
            context_seen.add(key)
            module_cg = self.project_cg.modules.get(context.target.module)
            summary = (module_cg.functions.get(context.target.qualname)
                       if module_cg is not None else None)
            return_values = (summary.return_values if summary is not None
                             else None)
            if return_values is None and summary is not None:
                return_values = summary.returns
            if return_values is None:
                candidates.append("unknown")
                continue
            if (len(context.edge.assigned_to) > 1
                    and self._is_tuple_return_source(return_values)):
                # Some legacy unpacked arguments retain the producing call
                # but not the selected index. Accept only a protocol shared
                # by every possible item, never the aggregate tuple owner.
                branches = (return_values.sources
                            if isinstance(return_values, SourceSet)
                            else (return_values,))
                return_values = make_source_set(
                    [item for branch in branches for item in branch.sources],
                    origin="return")
            candidates.extend(self._argument_method_owner_candidates(
                context.target.module, return_values, method, tracers,
                context_seen, receiver_class_filter, context))
        return self._dedupe_list(candidates) or ["unknown"]

    ## Resolve owner candidates for an argument, following parameter forwarding.
    #  @param module Module containing the argument expression.
    #  @param source Argument source.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Parameter recursion guard.
    #  @return Candidate owner strings.
    def _argument_owner_candidates(self, module, source, tracers, _seen=None):
        source = normalize_source(source)
        if source == "local":
            return ["local"]
        if isinstance(source, ContainerIter):
            container = normalize_source(source.container)
            if isinstance(container, ParameterSource):
                # An iterable element from a parameter is not evidence of a
                # project-local receiver.  Returning unknown here also keeps
                # local call-target matching from recursively resolving the
                # same parameterization edge.
                return ["unknown"]
        if isinstance(source, ContainerItem):
            container = normalize_source(source.container)
            if isinstance(container, ParameterSource):
                seen = set(_seen or set())
                key = ("pack-item", module, container.scope,
                       container.name, source.index)
                if key in seen:
                    return ["unknown"]
                seen.add(key)
                tracer = tracers.get(module)
                if tracer is None:
                    return ["unknown"]
                params = tracer.function_params.get(container.scope)
                if params is None:
                    params = tracer.function_params.get(
                        container.scope.rsplit(".", 1)[-1], [])
                if container.name in params:
                    arguments = self._parameter_pack_item_arguments(
                        module, container, source.index, tracers)
                    if not arguments:
                        return ["unknown"]
                    candidates = []
                    for arg_module, arg_source in arguments:
                        candidates.extend(self._argument_owner_candidates(
                            arg_module, arg_source, tracers, seen))
                    return self._dedupe_list(candidates) or ["unknown"]
                return ["unknown"]
        if not isinstance(source, ParameterSource):
            return self._origin_candidates(module, source, tracers)
        if source.derived or source.attributes:
            return ["unknown"]

        seen = set(_seen or set())
        key = (module, source.scope, source.name)
        if key in seen:
            return []
        seen.add(key)
        tracer = tracers.get(module)
        if tracer is None:
            return ["unknown"]
        params = tracer.function_params.get(source.scope)
        if params is None:
            params = tracer.function_params.get(
                source.scope.rsplit(".", 1)[-1], [])
        if source.name not in params:
            return ["unknown"]
        arguments = self._parameter_call_arguments(
            module, source.scope, source.name,
            params.index(source.name), tracer, tracers)
        if not arguments:
            return ["unknown"]
        candidates = []
        for arg_module, arg_source in arguments:
            candidates.extend(self._argument_owner_candidates(
                arg_module, arg_source, tracers, seen))
        return self._dedupe_list(candidates)

    ## Resolve a dotted parameter receiver through a local class attribute.
    #
    #  Supports bounded paths such as holder.payload.method() when holder is
    #  constructed locally and self.payload is bound from a constructor
    #  argument. Every constructor value must converge before ownership is
    #  returned.
    #  @param module Module containing the root argument.
    #  @param source Root argument source.
    #  @param attributes Receiver attributes after the parameter name.
    #  @param tracers Dict of module name to analyzer.
    #  @return Candidate owner strings.
    def _parameter_attribute_owner_candidates(self, module, source,
                                               attributes, tracers):
        if len(attributes) != 1:
            return ["unknown"]
        class_ref = self._local_class_from_source(module, source)
        if class_ref is None:
            return ["unknown"]
        class_module, class_name = class_ref
        module_cg = getattr(self, "project_cg", None)
        if module_cg is None or class_module not in module_cg.modules:
            return ["unknown"]
        class_summary = module_cg.modules[class_module].classes.get(class_name)
        class_tracer = tracers.get(class_module)
        if class_summary is None or class_tracer is None:
            return ["unknown"]
        attr_source = class_summary.attrs.get("self." + attributes[0])
        if attr_source is None:
            return ["unknown"]

        init_scope = class_name + ".__init__"
        init_params = class_tracer.function_params.get(init_scope, [])
        if isinstance(attr_source, str) and attr_source in init_params:
            attr_arguments = self._parameter_call_arguments(
                class_module, init_scope, attr_source,
                init_params.index(attr_source), class_tracer, tracers)
        else:
            attr_arguments = [(class_module, attr_source)]
        if not attr_arguments:
            return ["unknown"]
        candidates = []
        for arg_module, arg_source in attr_arguments:
            candidates.extend(self._argument_owner_candidates(
                arg_module, arg_source, tracers))
        return self._dedupe_list(candidates)

    ## Resolve a base-method field read through concrete subclass call edges.
    #
    #  A base class may read ``self.payload`` while a local subclass assigns
    #  that field from one of its method parameters. The lexical class alone
    #  cannot resolve the field. This helper finds the local runtime classes
    #  that actually reach the containing method, follows their field
    #  bindings through project call edges, and accepts only one converged
    #  callable owner.
    #  @param module Module containing the field read.
    #  @param source Structured instance-attribute source.
    #  @param method Method called on the field value.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Structured-source recursion guard.
    #  @return Converged owner string or "unknown".
    def _resolve_instance_attribute_method_top(
            self, module, source, method, tracers, _seen=None):
        if not source.scope or not source.class_name or not source.attribute:
            return "unknown"

        base_identity = (module, source.class_name)
        runtime_classes = []
        for caller_module, caller_cg in self.project_cg.modules.items():
            caller_tracer = tracers.get(caller_module)
            for edge in caller_cg.edges:
                if not self._edge_targets_local_function(
                        edge, caller_module, module, source.scope,
                        caller_tracer, tracers,
                        allow_inherited_dispatch=True):
                    continue
                candidates = self._local_class_candidates(
                    caller_module, edge.receiver_source, tracers)
                if (not candidates and edge.receiver_source == "self"):
                    caller_parts = edge.caller.qualname.rsplit(".", 1)
                    if len(caller_parts) == 2:
                        caller_class = caller_parts[0]
                        module_cg = self.project_cg.modules.get(caller_module)
                        if (module_cg is not None
                                and caller_class in module_cg.classes):
                            candidates = [(caller_module, caller_class)]
                for candidate in candidates:
                    if self._local_class_is_or_derives(
                            candidate[0], candidate[1],
                            base_identity[0], base_identity[1], tracers):
                        runtime_classes.append(candidate)

        runtime_classes = self._dedupe_list(runtime_classes)
        if not runtime_classes:
            return "unknown"

        owners = []
        for runtime_module, runtime_class in runtime_classes:
            bindings = self._local_class_attribute_bindings(
                runtime_module, runtime_class, source.attribute, tracers)
            if not bindings:
                owners.append("unknown")
                continue
            for binding_module, binding_source in bindings:
                candidates = self._argument_method_owner_candidates(
                    binding_module, binding_source, method, tracers,
                    _seen=set(_seen or set()),
                    receiver_class_filter=(runtime_module, runtime_class))
                owners.extend(candidates or ["unknown"])

        unique = self._dedupe_list(
            owner for owner in owners if owner not in (None, ""))
        if len(unique) == 1 and unique[0] != "unknown":
            return unique[0]
        return "unknown"
