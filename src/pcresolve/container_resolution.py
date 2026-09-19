## @package pcresolve.container_resolution
#  Resolve container item, iteration, and returned-element ownership.
#
#  The mixin owns bounded container evidence while ProjectAnalyzer supplies
#  project call contexts, recursive source resolution, and owner candidates.

from .builtin_ownership import _builtin_method_return_shape
from .ownership_contracts import (
    _has_result_owner_contract, _match_result_python_shape,
)
from .sources import (
    CallResult, ContainerItem, ContainerIter, DerivedResult, InstanceMethod,
    ParameterSource, PythonShape, SourceSet, TupleSource, UnknownSource,
    is_structured_source, normalize_source, source_display,
)


## Select one field from a bounded tuple/list source.
#  @param source Candidate tuple/list source.
#  @param index Zero-based field index.
#  @return Field source, or None when the field is not proven.
def _tuple_source_item(source, index):
    source = normalize_source(source)
    if not isinstance(source, TupleSource) or not isinstance(index, int):
        return None
    if index < 0 or index >= len(source.items):
        return None
    return normalize_source(source.items[index])


## Resolve container ownership through project-level provenance facts.
class ContainerResolutionMixin:
    ## Normalize a container index to its positive equivalent.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param container_name Name of the container variable.
    #  @param key_idx Raw index (may be negative).
    #  @return Adjusted index.
    def _container_index(self, tracer, container_name, key_idx):
        if not isinstance(key_idx, int):
            return key_idx
        if key_idx >= 0:
            return key_idx
        n = tracer.container_lengths.get(container_name)
        if n is not None:
            return key_idx + n
        return key_idx

    ## Resolve a container item access to its source symbol.
    #
    #  Looks up the item in the current module's container_items, and falls
    #  back to cross-file import if not found locally.
    #  @param module The module where the access occurs.
    #  @param container_name Name of the container variable.
    #  @param key_idx The index/key being accessed.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (src_module, src_symbol) tuple, or None.
    def _resolve_container_item(self, module, container_name, key_idx, tracers):
        tracer = tracers.get(module)
        if not tracer:
            return None
        container_idx = self._container_index(tracer, container_name, key_idx)
        item_key = (container_name, container_idx)
        if item_key in tracer.container_items:
            return (module, tracer.container_items[item_key])
        container_direct = tracer.symbols.direct.get(container_name)
        if self.is_local(container_direct):
            src_module = container_direct
            src_tracer = tracers.get(src_module)
            if not src_tracer:
                return None
            container_idx_src = self._container_index(src_tracer, container_name, key_idx)
            src_key = (container_name, container_idx_src)
            if src_key in src_tracer.container_items:
                return (src_module, src_tracer.container_items[src_key])
        return None

    ## Add a candidate to the list if not already visited.
    #  @param module The current module.
    #  @param src The source symbol.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @param candidates List to append to.
    #  @param visited Set of already-visited origins.
    def _container_candidate(self, module, src, tracers, candidates, visited):
        if not src:
            return
        top_src = self._top_source(module, src, tracers)
        if top_src and top_src not in visited:
            visited.add(top_src)
            candidates.append(top_src)

    ## Collect all candidates for a container's iteration source.
    #  @param module The current module.
    #  @param tracer The SingleFileAnalyzer for the module.
    #  @param container_name Name of the container variable.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return List of candidate source symbols.
    def _collect_container_candidates(self, module, tracer, container_name, tracers):
        candidates = []
        visited = set()
        for (cont_name, idx), src in tracer.container_items.items():
            if cont_name == container_name:
                self._container_candidate(module, src, tracers, candidates, visited)
        for src in sorted(
                tracer.container_set_sources.get(container_name, set()),
                key=source_display):
            self._container_candidate(module, src, tracers, candidates, visited)
        return candidates

    ## Resolve Python element shapes carried by an iterable argument.
    #
    #  This uses only a concrete PythonShape already recorded at a call site.
    #  A dictionary's value shape is not reused for iteration because Python
    #  iteration yields keys, not values. Unknown or mixed shapes remain
    #  unknown.
    #  @param source Argument source or PythonShape.
    #  @return List of element sources, or None when no Python shape was
    #  proven for this argument.
    def _python_iterable_element_sources(self, source):
        source = normalize_source(source)
        if isinstance(source, PythonShape):
            if source.kind == "str":
                return [source]
            if source.kind in ("list", "tuple", "set") and source.item_kind:
                return [PythonShape(source.item_kind)]
            return None
        if isinstance(source, SourceSet):
            candidates = []
            for item in source.sources:
                item_sources = self._python_iterable_element_sources(item)
                if item_sources is None:
                    return None
                candidates.extend(item_sources)
            return self._dedupe_list(candidates) or ["unknown"]
        return None

    ## Resolve a concrete Python protocol through exact local return contexts.
    #  @param module Source module.
    #  @param source Value source, distinct from its primary owner.
    #  @param tracers Per-module analyzers.
    #  @param context Enclosing local call context, when available.
    #  @param seen Recursion guard.
    #  @return Uniform PythonShape, or None for mixed or unsupported values.
    def _returned_python_shape(self, module, source, tracers,
                               context=None, seen=None):
        key = (module, repr(source),
               (context.caller_module, context.edge.call_lineno,
                context.edge.call_col_offset, context.target)
               if context is not None else None)
        if key in self._python_shape_in_progress:
            return None
        self._python_shape_in_progress.add(key)
        try:
            return self._infer_returned_python_shape(
                module, source, tracers, context, seen)
        finally:
            self._python_shape_in_progress.remove(key)

    ## Infer a Python shape while the cross-resolver recursion guard is held.
    #  @param module Source module.
    #  @param source Value source.
    #  @param tracers Per-module analyzers.
    #  @param context Exact local call context.
    #  @param seen Path-local recursion guard.
    #  @return Proven PythonShape or None.
    def _infer_returned_python_shape(self, module, source, tracers,
                                     context=None, seen=None):
        source = normalize_source(source)
        if isinstance(source, PythonShape):
            return source
        key = ("python-return-shape", module, repr(source),
               (context.caller_module, context.edge.call_lineno,
                context.edge.call_col_offset, context.target)
               if context is not None else None)
        seen = set(seen or set())
        if key in seen:
            return None
        seen.add(key)

        def uniform(values):
            result = None
            for value in values:
                if value is None or (result is not None and value != result):
                    return None
                result = value
            return result

        if isinstance(source, SourceSet):
            return uniform(
                self._returned_python_shape(module, item, tracers, context, seen)
                for item in source.sources)
        if (isinstance(source, DerivedResult) and source.kind == 'method_result'
                and len(source.sources) == 1):
            return self._returned_python_shape(
                module, source.sources[0], tracers, context, seen)
        if isinstance(source, ParameterSource):
            if source.attributes or (source.derived
                                    and source.derived_operation != "slice"):
                return None
            current = context
            while current is not None:
                if (module == current.target.module
                        and source.scope == current.target.qualname):
                    summary = self.project_cg.modules[module].functions[
                        source.scope]
                    if source.name not in summary.params:
                        return None
                    arguments = self._edge_parameter_sources(
                        current.edge, summary, source.name,
                        summary.params.index(source.name),
                        prefer_protocol_shape=True)
                    shape = uniform(
                        self._returned_python_shape(
                            current.caller_module, argument, tracers,
                            current.parent, seen)
                        for argument in arguments or [])
                    break
                current = current.parent
            else:
                tracer = tracers.get(module)
                params = (tracer.function_params.get(source.scope, [])
                          if tracer is not None else [])
                if source.name not in params:
                    return None
                arguments = self._parameter_call_arguments(
                    module, source.scope, source.name, params.index(source.name),
                    tracer, tracers, prefer_protocol_shape=True)
                shape = uniform(
                    self._returned_python_shape(origin, argument, tracers,
                                                None, seen)
                    for origin, argument in arguments)
            if source.derived and (shape is None or shape.kind not in (
                    "str", "bytes", "list", "tuple")):
                return None
            return shape
        if isinstance(source, CallResult):
            origin = source.source_module or module
            contexts = self._bounded_call_contexts(
                origin, source.call_lineno, source.call_col_offset, tracers,
                parent=context, callee_name=source.display_name)
            if contexts:
                shapes = []
                for called in contexts:
                    if (called.target.qualname.endswith(".__init__")
                            and not called.edge.callee_name.endswith(".__init__")):
                        return None
                    summary = self.project_cg.modules[
                        called.target.module].functions[called.target.qualname]
                    shapes.append(self._returned_python_shape(
                        called.target.module, summary.return_values,
                        tracers, called, seen))
                    if shapes[-1] is None or shapes[-1] != shapes[0]:
                        return None
                return uniform(shapes)
            if source.result_source is not None:
                return self._returned_python_shape(
                    origin, source.result_source, tracers, context, seen)
            return None
        if isinstance(source, InstanceMethod):
            receiver = source.receiver
            if (source.parameter_scope and source.parameter_name
                    and receiver == source.parameter_name):
                receiver = ParameterSource(source.parameter_scope,
                                           source.parameter_name)
            shape = self._returned_python_shape(
                module, receiver, tracers, context, seen)
            result = _builtin_method_return_shape(shape, source.method)
            if result is not None:
                return result
            # Reuse an already verified external result contract only.
            if not _has_result_owner_contract(source.method):
                return None
            owners = self._origin_candidates(module, receiver, tracers)
            if len(owners) == 1:
                return _match_result_python_shape(owners[0], source.method)
        if isinstance(source, ContainerItem):
            shape = self._returned_python_shape(
                module, source.container, tracers, context, seen)
            if shape is not None:
                if shape.kind == "str":
                    return PythonShape("str")
                if shape.kind in ("list", "tuple") and shape.item_kind:
                    return PythonShape(shape.item_kind)
        return None

    ## Resolve project-returned elements without erasing their value sources.
    #  @param module Module containing the source expression.
    #  @param source Element source, or iterable when iterable is True.
    #  @param tracers Per-module analyzers.
    #  @param context Exact return-call context, if available.
    #  @param iterable Whether to select elements from this source.
    #  @param _seen Recursion guard.
    #  @return (module, source) pairs, or None without an iterable contract.
    def _returned_element_sources(self, module, source, tracers,
                                  context=None, iterable=False, _seen=None):
        source = normalize_source(source)
        context_key = ((context.caller_module, context.edge.call_lineno,
                        context.edge.call_col_offset, context.target)
                       if context is not None else None)
        key = ("returned-element", module, source_display(source),
               context_key, iterable)
        seen = set(_seen or set())
        if key in seen:
            return [(module, UnknownSource("recursive returned iterable"))]
        seen.add(key)

        if isinstance(source, SourceSet):
            elements = []
            for branch in source.sources:
                elements.extend(self._returned_element_sources(
                    module, branch, tracers, context, iterable, seen)
                    or [(module, UnknownSource("unresolved return branch"))])
            return elements
        if isinstance(source, ContainerIter):
            return self._returned_element_sources(
                module, source.container, tracers, context, True, seen)
        if isinstance(source, ParameterSource):
            if source.derived or source.attributes:
                return None
            current = context
            while current is not None:
                if (module == current.target.module
                        and source.scope == current.target.qualname):
                    summary = self.project_cg.modules[
                        module].functions[current.target.qualname]
                    if source.name not in summary.params:
                        return None
                    arguments = self._edge_parameter_sources(
                        current.edge, summary, source.name,
                        summary.params.index(source.name),
                        prefer_protocol_shape=True)
                    elements = []
                    for argument in arguments or [UnknownSource()]:
                        elements.extend(self._returned_element_sources(
                            current.caller_module, argument, tracers,
                            current.parent, iterable, seen)
                            or [(current.caller_module, UnknownSource())])
                    return elements
                current = current.parent
            tracer = tracers.get(module)
            params = (tracer.function_params.get(source.scope, [])
                      if tracer is not None else [])
            if source.name not in params:
                return None
            arguments = self._parameter_call_arguments(
                module, source.scope, source.name, params.index(source.name),
                tracer, tracers, prefer_protocol_shape=True)
            elements = []
            for argument_module, argument in arguments:
                resolved = self._returned_element_sources(
                    argument_module, argument, tracers, None, iterable, seen)
                if resolved is None:
                    # The ordinary parameter-iteration path also retains
                    # literal element facts on call edges. Let it handle
                    # arguments not described by a return context here.
                    return None
                elements.extend(resolved)
            return elements or None
        if not iterable:
            return [(module, source)]
        shape = self._returned_python_shape(module, source, tracers, context)
        if shape is not None:
            shapes = self._python_iterable_element_sources(shape)
            if shapes is not None:
                return [(module, item) for item in shapes]
        shapes = self._python_iterable_element_sources(source)
        if shapes is not None:
            return [(module, shape) for shape in shapes]
        if isinstance(source, TupleSource):
            return [(module, item) for item in source.items]
        if isinstance(source, CallResult):
            origin = source.source_module or module
            contexts = self._bounded_call_contexts(
                origin, source.call_lineno, source.call_col_offset,
                tracers, parent=context, callee_name=source.display_name)
            if not contexts:
                shapes = self._python_iterable_element_sources(
                    source.result_source)
                return ([(origin, shape) for shape in shapes]
                        if shapes is not None else None)
            elements = []
            for called in contexts:
                tracer = tracers[called.target.module]
                summary = self.project_cg.modules[
                    called.target.module].functions[called.target.qualname]
                # A generator's return value terminates iteration; only its
                # yield summary describes values observed by a for-loop.
                returned = ([summary.yields] if summary.yields is not None
                            else tracer.return_element_sources.get(
                                called.target.qualname))
                for element in returned or [UnknownSource()]:
                    elements.extend(self._returned_element_sources(
                        called.target.module, element, tracers, called,
                        False, seen)
                        or [(called.target.module, UnknownSource())])
            return elements
        return None

    ## Resolve an iteration over a container to its source(s).
    #  @param module The current module.
    #  @param container_name Name of the container variable.
    #  @param tracers Dict of module_name -> SingleFileAnalyzer.
    #  @return (src_module, candidates_list) tuple, or None.
    def _resolve_container_iter(self, module, container_name, tracers):
        tracer = tracers.get(module)
        if not tracer:
            return None
        elements = self._returned_element_sources(
            module, container_name, tracers, iterable=True)
        if elements is not None:
            candidates = []
            for origin, element in elements:
                candidates.extend(self._origin_candidates(
                    origin, element, tracers, include_local=True))
            return (module, self._dedupe_list(candidates) or ["unknown"])
        if not isinstance(container_name, str):
            cn = normalize_source(container_name)
            if isinstance(cn, ParameterSource):
                if cn.derived or cn.attributes:
                    return (module, ["unknown"])
                params = (
                    tracer.function_params.get(cn.scope)
                    or tracer.function_params.get(
                        cn.scope.rsplit(".", 1)[-1], []))
                if cn.name not in params:
                    return (module, ["unknown"])
                param_index = params.index(cn.name)
                protocol_arguments = self._parameter_call_arguments(
                    module, cn.scope, cn.name, param_index,
                    tracer, tracers, prefer_protocol_shape=True)
                if protocol_arguments:
                    element_sources = []
                    protocol_proven = True
                    for _, argument in protocol_arguments:
                        argument_sources = (
                            self._python_iterable_element_sources(argument))
                        if argument_sources is None:
                            protocol_proven = False
                            break
                        element_sources.extend(argument_sources)
                    if protocol_proven and element_sources:
                        return (
                            module,
                            self._dedupe_list(element_sources) or ["unknown"],
                        )
                arguments = self._parameter_call_arguments(
                    module, cn.scope, cn.name, param_index,
                    tracer, tracers, prefer_iterable_elements=True)
                if not arguments:
                    return (module, ["unknown"])
                candidates = []
                for caller_module, source in arguments:
                    candidates.extend(self._origin_candidates(
                        caller_module, source, tracers,
                        include_local=True))
                return (
                    module,
                    self._dedupe_list(candidates) or ["unknown"],
                )
            if isinstance(cn, CallResult) and isinstance(cn.callee, str):
                elements = tracer.return_element_sources.get(cn.callee)
                if elements is not None:
                    candidates = []
                    for element in elements:
                        candidates.extend(self._origin_candidates(
                            module, element, tracers, include_local=True))
                    return (module, self._dedupe_list(candidates) or ["unknown"])
                top = self._top_source(module, cn.callee, tracers)
                if top and top not in ("local", "python", "unknown", ""):
                    ## 1.0.5 P2: only propagate callee top as element type
                    #  when the callee has explicit return-type evidence.
                    #  Without return_sources, an import-backed call result
                    #  has no yield contract — element type is unknowable.
                    if tracer.return_sources.get(cn.callee) is not None:
                        return (module, [top])
                ## No yield contract or builtin callee:
                #  element type cannot be determined statically.
                return (module, ["unknown"])
            return (module, ["unknown"])
        local_candidates = self._collect_container_candidates(
            module, tracer, container_name, tracers)
        if local_candidates:
            return (module, local_candidates)
        container_direct = tracer.symbols.direct.get(container_name)
        if isinstance(container_direct, str) and self.is_local(container_direct):
            src_module = container_direct
            src_tracer = tracers.get(src_module)
            if not src_tracer:
                return None
            src_candidates = self._collect_container_candidates(
                src_module, src_tracer, container_name, tracers)
            if src_candidates:
                return (src_module, src_candidates)
        return None

    ## Resolve one structured container-item source.
    #  @param module Module containing the item access.
    #  @param a Container source extracted by the dispatcher.
    #  @param b Item index or key extracted by the dispatcher.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Structured-source recursion guard.
    #  @return Resolved display, module, and owner tuple.
    def _resolve_container_item_source(self, module, a, b, tracers, _seen):
        if isinstance(a, TupleSource):
            selected = _tuple_source_item(a, b)
            if selected is not None:
                structured = self._resolve_structured_source(
                    module, selected, tracers, _seen=set(_seen))
                if structured is not None:
                    _, src_module, src_symbol = structured
                    return (f"{source_display(a)}[{b}]",
                            src_module, src_symbol)
        if isinstance(a, ParameterSource):
            tracer = tracers.get(module)
            params = (tracer.function_params.get(a.scope)
                      if tracer is not None else None)
            if params is None and tracer is not None:
                params = tracer.function_params.get(
                    a.scope.rsplit(".", 1)[-1], [])
            if tracer is not None and a.name in (params or []):
                arguments = self._parameter_call_arguments(
                    module, a.scope, a.name, params.index(a.name),
                    tracer, tracers, prefer_iterable_elements=True)
                selected_sources = []
                for _, argument in arguments:
                    selected = _tuple_source_item(argument, b)
                    if selected is not None:
                        selected_sources.append(selected)
                selected_sources = self._dedupe_list(
                    selected_sources)
                if len(selected_sources) == 1:
                    structured = self._resolve_structured_source(
                        module, selected_sources[0], tracers,
                        _seen=set(_seen))
                    if structured is not None:
                        _, src_module, src_symbol = structured
                        return (f"{source_display(a)}[{b}]",
                                src_module, src_symbol)
        resolved = self._resolve_container_item(module, a, b, tracers)
        if resolved:
            src_module, src_symbol = resolved
            return (f"{a}[{b}]", src_module, src_symbol)
        if is_structured_source(a):
            structured = self._resolve_structured_source(
                module, a, tracers, _seen=set(_seen))
            if structured is not None:
                _, src_module, src_symbol = structured
                top = self._top_source(
                    src_module, src_symbol, tracers, _seen=set(_seen))
                if top and top not in ("local", "unknown", ""):
                    return (f"{a}[{b}]", src_module, top)
        return (f"{a}[{b}]", module, a)

    ## Resolve one structured container-iteration source.
    #  @param module Module containing the iteration.
    #  @param a Container source extracted by the dispatcher.
    #  @param tracers Dict of module name to analyzer.
    #  @return Resolved display, module, and owner tuple.
    def _resolve_container_iter_source(self, module, a, tracers):
        resolved = self._resolve_container_iter(module, a, tracers)
        if not resolved:
            ## Cannot determine element type — conservative fallback.
            return (f"{a}[*]", module, "unknown")
        src_module, candidates = resolved
        if len(candidates) == 1:
            src_symbol = candidates[0]
        elif any(candidate in ("local", "python", "unknown", "")
                 for candidate in candidates):
            src_symbol = "unknown"
        else:
            src_symbol = "[" + ",".join(candidates) + "]"
        return (f"{a}[*]", src_module, src_symbol)
