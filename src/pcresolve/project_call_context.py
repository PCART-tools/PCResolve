## @package pcresolve.project_call_context
#  Exact project call targets, bounded contexts, and parameter binding.

from .call_graph import FunctionId, ProjectCallGraph
from .call_resolution import CallContext, DefinitionRecord, DefinitionIndex
from .program_facts import (
    bind_parameter_sources, starred_item_source,
    CONTEXT_BINDING, OWNERSHIP_BINDING,
)
from .return_resolution import CallBinding, first_bound_value
from .sources import (
    CallResult, ContainerItem, DerivedResult, InstanceMethod, ParameterSource,
    SourceSet, TupleSource, UnknownSource, normalize_source, source_display,
)


_NO_BOUNDED_CANDIDATES = object()


## Project call-context and argument-binding behavior mixed into ProjectAnalyzer.
class ProjectCallContextMixin:
    ## Adapt this generation's ownership summaries to the shared name index.
    #  Logical keys and mutable source payloads retain their ownership meaning.
    #  A normal analysis collects a new ProjectCallGraph before resolution.
    #  @return Internal candidate index; not a public call-graph result.
    def _get_definition_index(self):
        if getattr(self, '_definition_index_graph', None) is not self.project_cg:
            records = []
            for module, module_cg in self.project_cg.modules.items():
                for kind, summaries in (('function', module_cg.functions), ('class', module_cg.classes)):
                    records.extend(DefinitionRecord(module, qualname, summary, kind,
                                                    summary.definition_span)
                                   for qualname, summary in summaries.items())
            self._definition_index = DefinitionIndex(records)
            self._definition_index_graph = self.project_cg
        return self._definition_index

    ## Find all project-local functions reached by one call edge.
    #
    #  @param edge Call edge to resolve.
    #  @param caller_module Module containing the edge.
    #  @param tracers Dict of module name to analyzer.
    #  @return List of matching FunctionId values.
    def _local_edge_targets(self, edge, caller_module, tracers):
        if getattr(edge, "mapping_targets", None) is not None:
            if not edge.mapping_targets_complete:
                return []
            return list(edge.mapping_targets)
        targets = []
        caller_tracer = tracers.get(caller_module)
        candidates = self._get_definition_index().records_for()
        for candidate in candidates:
            if self._edge_targets_local_function(
                    edge, caller_module, candidate.module, candidate.qualname,
                    caller_tracer, tracers):
                targets.append(candidate.payload.id)
        # An exact subclass method wins over inherited implementations. When
        # no exact method exists, resolve the nearest available local base
        # implementation through the class graph. Multiple inherited targets
        # remain explicit and therefore cannot drive bounded result binding.
        if not targets:
            for candidate in candidates:
                if self._edge_targets_local_function(
                        edge, caller_module, candidate.module, candidate.qualname,
                        caller_tracer, tracers,
                        allow_inherited_dispatch=True):
                    targets.append(candidate.payload.id)
            targets = self._nearest_inherited_method_targets(
                targets, tracers)
        unique = []
        seen = set()
        for target in targets:
            key = (target.module, target.qualname)
            if key not in seen:
                seen.add(key)
                unique.append(target)
        return unique

    ## Remove ancestor methods hidden by a more-derived local implementation.
    #
    #  Multiple-inheritance siblings remain separate candidates because this
    #  bounded resolver does not claim a complete Python MRO. A linear local
    #  inheritance chain, however, has one unambiguous nearest implementation.
    #  @param targets Candidate inherited FunctionId values.
    #  @param tracers Dict of module name to analyzer.
    #  @return Candidate list with shadowed ancestor methods removed.
    def _nearest_inherited_method_targets(self, targets, tracers):
        class_targets = {}
        for target in targets:
            module_cg = self.project_cg.modules.get(target.module)
            parts = target.qualname.rsplit(".", 1)
            if (module_cg is not None and len(parts) == 2
                    and parts[0] in module_cg.classes
                    and parts[1] in module_cg.classes[parts[0]].methods):
                class_targets[target] = (target.module, parts[0])

        nearest = []
        for target in targets:
            target_class = class_targets.get(target)
            if target_class is None:
                nearest.append(target)
                continue
            shadowed = any(
                other != target
                and self._local_class_is_or_derives(
                    other_class[0], other_class[1],
                    target_class[0], target_class[1], tracers)
                for other, other_class in class_targets.items()
            )
            if not shadowed:
                nearest.append(target)
        return nearest

    ## Resolve every branch of an explicit local callable SourceSet.
    #
    #  This deliberately rejects inferred method-name candidates. Multiple
    #  targets are safe to converge only when the call edge itself retains
    #  each exact project-local callable selected by source control flow.
    #  @param edge Call edge containing callable provenance.
    #  @param caller_module Module containing the edge.
    #  @return List of exact FunctionId values, or an empty list.
    def _explicit_local_callable_targets(self, edge, caller_module):
        if getattr(edge, "mapping_targets", None) is not None:
            return (list(edge.mapping_targets)
                    if edge.mapping_targets_complete else [])
        source = normalize_source(getattr(edge, "callee_source", None))
        if not isinstance(source, SourceSet):
            return []
        targets = []
        seen = set()
        for branch in source.sources:
            branch = normalize_source(branch)
            if not isinstance(branch, str):
                return []
            matches = self._get_definition_index().find_qualified(
                [branch], local_module=caller_module, local_names=[branch])
            if len(matches) != 1:
                return []
            target = matches[0].id
            key = (target.module, target.qualname)
            if key not in seen:
                seen.add(key)
                targets.append(target)
        return targets

    ## Build all project-local contexts from one exact call-site position.
    #
    #  Multiple contexts are retained for a statically enumerated callable
    #  branch. Their result owners are converged by the caller.
    #  @param caller_module Module containing the call.
    #  @param call_lineno Call line number.
    #  @param call_col_offset Call column offset.
    #  @param tracers Dict of module name to analyzer.
    #  @param parent Enclosing forwarding context.
    #  @param callee_name Optional syntactic callee to distinguish nested calls
    #  sharing their start position.
    #  @return List of CallContext values.
    def _bounded_call_contexts(self, caller_module, call_lineno,
                               call_col_offset, tracers, parent=None,
                               callee_name=None):
        module_cg = self.project_cg.modules.get(caller_module)
        if module_cg is None or not call_lineno:
            return []
        edges = [
            edge for edge in module_cg.edges
            if edge.call_lineno == call_lineno
            and edge.call_col_offset == call_col_offset
        ]
        if len(edges) > 1 and callee_name:
            edges = [edge for edge in edges
                     if edge.callee_name == callee_name]
        if len(edges) != 1:
            return []
        targets = self._local_edge_targets(edges[0], caller_module, tracers)
        if len(targets) > 1:
            targets = self._explicit_local_callable_targets(
                edges[0], caller_module)
            if len(targets) <= 1:
                return []
        return [
            CallContext(
                caller_module=caller_module,
                target=target,
                edge=edges[0],
                parent=parent,
            )
            for target in targets
        ]

    ## Build one exact bounded context from a call-site position.
    #
    #  @param caller_module Module containing the call.
    #  @param call_lineno Call line number.
    #  @param call_col_offset Call column offset.
    #  @param tracers Dict of module name to analyzer.
    #  @param parent Enclosing forwarding context.
    #  @return CallContext when edge and target are unique, otherwise None.
    def _bounded_call_context(self, caller_module, call_lineno,
                              call_col_offset, tracers, parent=None):
        contexts = self._bounded_call_contexts(
            caller_module, call_lineno, call_col_offset, tracers,
            parent=parent)
        if len(contexts) != 1:
            return None
        return contexts[0]

    ## Read the argument supplied to one parameter in a bounded context.
    #
    #  @param context Exact local call context.
    #  @param parameter Target parameter name.
    #  @return Argument source or None.
    def _bounded_argument_source(self, context, parameter):
        module_cg = self.project_cg.modules.get(context.target.module)
        summary = (
            module_cg.functions.get(context.target.qualname)
            if module_cg is not None else None)
        if summary is None or parameter not in summary.params:
            return None
        edge = context.edge
        values = bind_parameter_sources(
            summary.signature, parameter, edge.arg_sources.get('pos', {}),
            edge.arg_sources.get('kw', {}), getattr(edge, 'star_arg_sources', {}),
            getattr(edge, 'star_kwarg_sources', []), ContainerItem, CONTEXT_BINDING)
        bindings = (CallBinding('parameter', parameter, tuple(values)),) if values else ()
        return first_bound_value(bindings, 'parameter', parameter)

    ## Resolve one positional parameter from a starred call argument.
    #  @param edge Call graph edge.
    #  @param summary Callee signature summary.
    #  @param index Zero-based positional parameter index.
    #  @return ContainerItem selecting the pack item, or None.
    def _star_positional_item_source(self, edge, summary, index):
        return starred_item_source(getattr(edge, 'star_arg_sources', {}), index, ContainerItem)

    ## Resolve one selected item from a local variadic parameter under a
    #  bounded call context.
    #  @param context Current exact call context.
    #  @param pack_source ParameterSource naming *args or **kwargs.
    #  @param index Integer position or keyword name.
    #  @return (caller module, source, parent context), or None.
    def _bounded_pack_item_source(self, context, pack_source, index):
        if not isinstance(pack_source, ParameterSource):
            return None
        for current in context.chain() if context is not None else ():
            if pack_source.scope != current.target.qualname:
                continue
            module_cg = self.project_cg.modules.get(current.target.module)
            summary = (
                module_cg.functions.get(current.target.qualname)
                if module_cg is not None else None)
            if summary is None:
                return None
            edge = current.edge
            if pack_source.name == summary.vararg:
                if not isinstance(index, int):
                    return None
                positional_params = list(
                    getattr(summary, "positional_params", []))
                actual_index = len(positional_params) + index
                positional = edge.arg_sources.get("pos", {})
                if actual_index in positional:
                    return (current.caller_module,
                            positional[actual_index], current.parent)
                star_item = self._star_positional_item_source(
                    edge, summary, actual_index)
                if star_item is not None:
                    return (current.caller_module,
                            star_item, current.parent)
                return None
            if pack_source.name == summary.kwarg:
                if not isinstance(index, str):
                    return None
                keyword_args = edge.arg_sources.get("kw", {})
                if index in keyword_args:
                    return (current.caller_module,
                            keyword_args[index], current.parent)
                star_kwargs = getattr(edge, "star_kwarg_sources", [])
                if len(star_kwargs) == 1:
                    return (current.caller_module,
                            ContainerItem(star_kwargs[0], index),
                            current.parent)
                return None
            return None
        return None

    ## Resolve a constructor parameter referenced by a method return summary.
    #
    #  For Holder.expose() returning the value stored by Holder.__init__,
    #  use the exact receiver constructor edge. No class-name or library-name
    #  table is involved.
    #
    #  @param context Current method-call context.
    #  @param source Constructor ParameterSource.
    #  @param tracers Dict of module name to analyzer.
    #  @return Candidate owner strings or None when not applicable.
    def _constructor_parameter_candidates(self, context, source, tracers,
                                          _seen):
        if not isinstance(source, ParameterSource):
            return None
        if not source.scope.endswith(".__init__"):
            return None
        class_name = source.scope.rsplit(".", 1)[0]
        method_class = (
            context.target.qualname.rsplit(".", 1)[0]
            if "." in context.target.qualname else "")
        if class_name != method_class:
            return None
        receiver_source = normalize_source(context.edge.receiver_source)
        if not isinstance(receiver_source, CallResult):
            return ["unknown"]
        ctor_context = self._bounded_call_context(
            context.caller_module,
            receiver_source.call_lineno,
            receiver_source.call_col_offset,
            tracers,
            parent=context.parent,
        )
        if (ctor_context is None
                or ctor_context.target.module != context.target.module
                or ctor_context.target.qualname != source.scope):
            return ["unknown"]
        argument = self._bounded_argument_source(
            ctor_context, source.name)
        if argument is None:
            return ["unknown"]
        return self._bounded_source_candidates(
            ctor_context.caller_module, argument, ctor_context.parent,
            tracers, _seen)

    ## Evaluate a source under one exact local call context.
    #
    #  Parameter substitution is bounded by exact call positions. Nested local
    #  calls carry the current context as their parent, which supports simple
    #  forwarding without merging unrelated call sites.
    #
    #  @param source_module Module where source was evaluated.
    #  @param source Source value to resolve.
    #  @param context Current CallContext or None.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Recursion guard.
    #  @return Candidate owner strings.
    def _bounded_source_candidates(self, source_module, source, context,
                                   tracers, _seen):
        source = normalize_source(source)
        context_key = (
            context.target.module,
            context.target.qualname,
            context.edge.call_lineno,
            context.edge.call_col_offset,
        ) if context is not None else ("", "", 0, 0)
        key = (
            "bounded-source", source_module, context_key,
            type(source).__name__, source_display(source),
        )
        if key in _seen:
            return ["unknown"]
        seen = set(_seen)
        seen.add(key)

        candidates = self._bounded_aggregate_candidates(
            source_module, source, context, tracers, seen)
        if candidates is not _NO_BOUNDED_CANDIDATES:
            return candidates
        candidates = self._bounded_parameter_candidates(
            source_module, source, context, tracers, seen)
        if candidates is not _NO_BOUNDED_CANDIDATES:
            return candidates
        candidates = self._bounded_named_parameter_candidates(
            source, context, tracers, seen)
        if candidates is not _NO_BOUNDED_CANDIDATES:
            return candidates
        if isinstance(source, CallResult):
            return self._bounded_call_source_candidates(
                source_module, source, context, tracers, seen)
        return self._origin_candidates(
            source_module, source, tracers, _seen=seen)

    ## Resolve SourceSet, DerivedResult, and container aggregates.
    #  @return Candidate owners, or the module sentinel when not applicable.
    def _bounded_aggregate_candidates(self, source_module, source, context,
                                      tracers, seen):
        if isinstance(source, SourceSet):
            candidates = []
            for item in source.sources:
                candidates.extend(self._bounded_source_candidates(
                    source_module, item, context, tracers, set(seen)))
            return self._dedupe_list(candidates) or ["unknown"]
        if isinstance(source, UnknownSource):
            return ["unknown"]
        if (isinstance(source, DerivedResult)
                and source.kind == "receiver_preserving_ufunc"):
            candidate_groups = [
                self._bounded_source_candidates(
                    source_module, item, context, tracers, set(seen))
                for item in source.sources
            ]
            return [self._receiver_preserving_ufunc_owner(candidate_groups)]
        if (isinstance(source, DerivedResult)
                and source.kind == "expression"):
            candidate_groups = [
                (["python"] if self._returned_python_shape(
                    source_module, item, tracers, context) is not None else
                 self._bounded_source_candidates(
                     source_module, item, context, tracers, set(seen)))
                for item in source.sources
            ]
            return [self._bounded_expression_owner(candidate_groups)]
        if isinstance(source, ContainerItem):
            return self._bounded_container_item_candidates(
                source_module, source, context, tracers, seen)
        return _NO_BOUNDED_CANDIDATES

    ## Resolve a structured container selection in a bounded context.
    #  @return Candidate owners, or the module sentinel when not applicable.
    def _bounded_container_item_candidates(self, source_module, source,
                                           context, tracers, seen):
        container = normalize_source(source.container)
        if (isinstance(container, CallResult)
                and isinstance(source.index, int)):
            candidates = self._bounded_call_result_item_candidates(
                source_module, container, source.index, tracers,
                parent=context, _seen=seen)
            if candidates is not None:
                return candidates
            return self._bounded_source_candidates(
                source_module, container, context, tracers, seen)
        if not isinstance(container, ParameterSource):
            return _NO_BOUNDED_CANDIDATES
        selected = self._bounded_pack_item_source(
            context, container, source.index)
        if selected is None:
            return ["unknown"]
        selected_module, selected_source, next_context = selected
        return self._bounded_source_candidates(
            selected_module, selected_source, next_context, tracers, seen)

    ## Substitute an explicit ParameterSource through its bounded call chain.
    #  @return Candidate owners, or the module sentinel when not applicable.
    def _bounded_parameter_candidates(self, source_module, source, context,
                                      tracers, seen):
        if not isinstance(source, ParameterSource):
            return _NO_BOUNDED_CANDIDATES
        current = context
        while current is not None:
            if source.scope == current.target.qualname:
                argument = self._bounded_argument_source(
                    current, source.name)
                if argument is None:
                    return ["unknown"]
                return self._bounded_source_candidates(
                    current.caller_module, argument, current.parent,
                    tracers, seen)
            current = current.parent
        if context is not None:
            constructor_candidates = self._constructor_parameter_candidates(
                context, source, tracers, seen)
            if constructor_candidates is not None:
                return constructor_candidates
        candidates = self._argument_owner_candidates(
            source_module, source, tracers)
        return candidates or ["unknown"]

    ## Substitute a legacy string parameter through its bounded call chain.
    #  @return Candidate owners, or the module sentinel when not applicable.
    def _bounded_named_parameter_candidates(self, source, context,
                                            tracers, seen):
        if not isinstance(source, str) or context is None:
            return _NO_BOUNDED_CANDIDATES
        current = context
        while current is not None:
            module_cg = self.project_cg.modules.get(current.target.module)
            summary = (
                module_cg.functions.get(current.target.qualname)
                if module_cg is not None else None)
            if summary is not None and source in summary.params:
                argument = self._bounded_argument_source(current, source)
                if argument is None:
                    return ["unknown"]
                return self._bounded_source_candidates(
                    current.caller_module, argument, current.parent,
                    tracers, seen)
            current = current.parent
        return _NO_BOUNDED_CANDIDATES

    ## Resolve one CallResult under an exact bounded context.
    #  @return Candidate owner strings.
    def _bounded_call_source_candidates(self, source_module, source, context,
                                        tracers, seen):
        nested = self._bounded_call_result_candidates(
            source_module, source, tracers, parent=context, _seen=seen)
        if nested is not None:
            return nested
        if source.result_source is not None:
            if (isinstance(source.result_source, str)
                    and source.result_source not in (
                        "", "local", "python", "unknown")):
                return [source.result_source]
            return self._bounded_source_candidates(
                source.source_module or source_module,
                source.result_source, context, tracers, seen)
        if isinstance(source.callee, str):
            source_origin_module = source.source_module or source_module
            top = self._top_source(
                source_origin_module, source.callee, tracers, _seen=seen)
            return [top or "unknown"]
        return ["unknown"]

    ## Resolve one local call result with exact call-site substitutions.
    #
    #  @param caller_module Module containing the call.
    #  @param source CallResult to resolve.
    #  @param tracers Dict of module name to analyzer.
    #  @param parent Enclosing forwarding context.
    #  @param _seen Recursion guard.
    #  @return Candidate owners, or None when no unique local context exists.
    def _bounded_call_result_candidates(self, caller_module, source, tracers,
                                        parent=None, _seen=None):
        if not isinstance(source, CallResult):
            return None
        contexts = self._bounded_call_contexts(
            caller_module, source.call_lineno, source.call_col_offset,
            tracers, parent=parent)
        if not contexts:
            return None
        seen = set(_seen or set())
        candidates = []
        for context in contexts:
            module_cg = self.project_cg.modules.get(context.target.module)
            summary = (
                module_cg.functions.get(context.target.qualname)
                if module_cg is not None else None)
            if summary is None or summary.returns is None:
                if len(contexts) == 1:
                    return None
                candidates.append("unknown")
                continue
            key = (
                "bounded-call", caller_module, source.call_lineno,
                source.call_col_offset, context.target.module,
                context.target.qualname,
            )
            if key in seen:
                candidates.append("unknown")
                continue
            context_seen = set(seen)
            context_seen.add(key)
            # A tuple return has no owner for the aggregate object. It is only
            # meaningful after the caller binds a proven positional item into
            # CallResult.result_source. If no positional marker is available,
            # evaluate every tuple item and retain only a common owner.
            if self._is_tuple_return_source(summary.returns):
                if source.result_source is not None:
                    candidates.extend(self._bounded_source_candidates(
                        context.target.module, source.result_source, context,
                        tracers, context_seen))
                    continue
                tuple_source = normalize_source(summary.returns)
                tuple_lengths = []
                branches = (tuple_source.sources
                            if isinstance(tuple_source, SourceSet)
                            else (tuple_source,))
                for branch in branches:
                    if isinstance(branch, DerivedResult):
                        tuple_lengths.append(len(branch.sources))
                if not tuple_lengths:
                    candidates.append("unknown")
                    continue
                for index in range(min(tuple_lengths)):
                    selected = self._return_item_source(
                        summary.returns, index)
                    if selected is None:
                        candidates.append("unknown")
                        break
                    candidates.extend(self._bounded_source_candidates(
                        context.target.module, selected, context,
                        tracers, set(context_seen)))
                continue
            candidates.extend(self._bounded_source_candidates(
                context.target.module, summary.returns, context,
                tracers, context_seen))
        return self._dedupe_list(candidates) or ["unknown"]

    ## Resolve one positional item from an exact local tuple-return call.
    #
    #  @param caller_module Module containing the call.
    #  @param source CallResult for the tuple-producing local call.
    #  @param index Zero-based selected tuple position.
    #  @param tracers Dict of module name to analyzer.
    #  @param parent Enclosing forwarding context.
    #  @param _seen Recursion guard.
    #  @return Candidate owners, or None when no tuple context is proven.
    def _bounded_call_result_item_candidates(
            self, caller_module, source, index, tracers,
            parent=None, _seen=None):
        if not isinstance(source, CallResult) or not isinstance(index, int):
            return None
        context = self._bounded_call_context(
            caller_module, source.call_lineno, source.call_col_offset,
            tracers, parent=parent)
        if context is None:
            return None
        module_cg = self.project_cg.modules.get(context.target.module)
        summary = (
            module_cg.functions.get(context.target.qualname)
            if module_cg is not None else None)
        if summary is None or summary.returns is None:
            return None
        selected = self._return_item_source(summary.returns, index)
        if selected is None:
            return None
        seen = set(_seen or set())
        key = (
            "bounded-call-item", caller_module,
            source.call_lineno, source.call_col_offset,
            context.target.module, context.target.qualname, index,
        )
        if key in seen:
            return ["unknown"]
        seen.add(key)
        return self._bounded_source_candidates(
            context.target.module, selected, context, tracers, seen)

    ## Converge bounded candidates without guessing across owners.
    #
    #  @param candidates Candidate owner strings.
    #  @return One owner or "unknown".
    def _bounded_candidates_top(self, candidates):
        unique = self._dedupe_list([
            candidate for candidate in candidates
            if candidate not in (None, "")
        ])
        if not unique or "unknown" in unique or len(unique) != 1:
            return "unknown"
        return unique[0]

    ## Find a module containing import evidence for a bounded owner.
    #
    #  The owner itself remains the public result. This module is used only
    #  so the existing trace engine can validate that result against the
    #  import which produced it.
    #
    #  @param owner Converged owner name.
    #  @param default_module Calling module fallback.
    #  @param tracers Dict of module name to analyzer.
    #  @return Module name containing matching import evidence.
    def _bounded_owner_module(self, owner, default_module, tracers):
        if owner in ("local", "python", "unknown", "", None):
            return default_module
        default_tracer = tracers.get(default_module)
        if self._has_import_origin(default_tracer, owner):
            return default_module
        for candidate_module, tracer in tracers.items():
            if self._has_import_origin(tracer, owner):
                return candidate_module
        return default_module

    ## Collect arguments supplied to one local function parameter.
    #
    #  Combines the legacy same-file call-site table with project CallEdge
    #  facts. The latter preserves forward references and cross-file calls.
    #  Each physical call site is returned once.
    #
    #  @param module Defining module.
    #  @param scope_name Qualified function name.
    #  @param parameter Parameter name.
    #  @param param_index Positional parameter index.
    #  @param tracer Defining-module analyzer.
    #  @param tracers Dict of module name to analyzer.
    #  @param prefer_protocol_shape Prefer independently proven PythonShape
    #  evidence without changing ordinary call-target argument sources.
    #  @param prefer_iterable_elements Prefer independently preserved
    #  container element sources without treating the container as an item.
    #  @param receiver_class_filter Optional project-local runtime class
    #  required by a virtual-dispatch forwarding context.
    #  @return List of (caller module, argument source) tuples.
    def _parameter_call_arguments(self, module, scope_name, parameter,
                                  param_index, tracer, tracers,
                                  prefer_protocol_shape=False,
                                  prefer_iterable_elements=False,
                                  receiver_class_filter=None):
        found = []
        seen = set()
        self._collect_parameterized_arguments(
            module, scope_name, parameter, tracer, found, seen)
        self._collect_recorded_call_arguments(
            module, scope_name, param_index, tracer, found, seen,
            prefer_protocol_shape, prefer_iterable_elements,
            receiver_class_filter)
        if prefer_iterable_elements:
            self._collect_pool_map_arguments(
                scope_name, tracers, found, seen)
        self._collect_process_callback_arguments(
            module, scope_name, param_index, tracers, found, seen)
        self._collect_project_edge_arguments(
            module, scope_name, parameter, param_index, tracers,
            found, seen, prefer_protocol_shape,
            prefer_iterable_elements, receiver_class_filter)
        return found

    ## Add one argument while preserving the original cross-source identity.
    def _append_parameter_argument(self, found, seen, key,
                                   caller_module, source):
        if key in seen:
            return
        seen.add(key)
        found.append((caller_module, source))

    ## Collect explicit single-file parameterization facts.
    def _collect_parameterized_arguments(self, module, scope_name, parameter,
                                         tracer, found, seen):
        sources = tracer.parameter_sources.get((scope_name, parameter), [])
        for index, source in enumerate(sources):
            if source is None:
                continue
            key = ("parameterization", index, source_display(source))
            self._append_parameter_argument(
                found, seen, key, module, source)

    ## Collect legacy single-file call-site argument facts.
    def _collect_recorded_call_arguments(
            self, module, scope_name, param_index, tracer, found, seen,
            prefer_protocol_shape, prefer_iterable_elements,
            receiver_class_filter):
        if receiver_class_filter is not None:
            return
        bare_scope = scope_name.rsplit(".", 1)[-1]
        call_sites = (tracer.call_sites.get(scope_name)
                      or tracer.call_sites.get(bare_scope, []))
        for call_site in call_sites:
            if prefer_iterable_elements:
                continue
            args = call_site.get("args", [])
            if prefer_protocol_shape:
                protocol_args = call_site.get("protocol_args", [])
                if (param_index < len(protocol_args)
                        and protocol_args[param_index] is not None):
                    args = protocol_args
            if param_index >= len(args):
                continue
            arg_source = args[param_index]
            if arg_source is None:
                continue
            caller_module = call_site.get("module") or module
            key = (
                caller_module,
                call_site.get("lineno", 0),
                call_site.get("col_offset", 0),
            )
            self._append_parameter_argument(
                found, seen, key, caller_module, arg_source)

    ## Collect the supported multiprocessing.Pool.map callback argument.
    def _collect_pool_map_arguments(self, scope_name, tracers, found, seen):
        target_name = scope_name.rsplit(".", 1)[-1]
        cg = getattr(self, "project_cg", ProjectCallGraph())
        for caller_module, caller_cg in cg.modules.items():
            caller_tracer = tracers.get(caller_module)
            for edge in caller_cg.edges:
                if not self._is_multiprocessing_map_edge(
                        edge, caller_tracer):
                    continue
                callback_positions = [
                    position for position, callback_name
                    in getattr(edge, "callback_args", {}).items()
                    if callback_name == target_name
                ]
                if len(callback_positions) != 1:
                    continue
                iterable_position = callback_positions[0] + 1
                element_source = getattr(
                    edge, "iterable_arg_sources", {}).get(
                        "pos", {}).get(iterable_position)
                if (element_source is None
                        or isinstance(element_source, UnknownSource)):
                    continue
                key = (caller_module, edge.call_lineno,
                       edge.call_col_offset, source_display(element_source))
                self._append_parameter_argument(
                    found, seen, key, caller_module, element_source)

    ## Collect the supported multiprocessing.Process callback arguments.
    def _collect_process_callback_arguments(
            self, module, scope_name, param_index, tracers, found, seen):
        target_name = scope_name.rsplit(".", 1)[-1]
        cg = getattr(self, "project_cg", ProjectCallGraph())
        for caller_module, caller_cg in cg.modules.items():
            caller_tracer = tracers.get(caller_module)
            for edge in caller_cg.edges:
                if not self._is_multiprocessing_process_edge(
                        edge, caller_tracer):
                    continue
                for binding in getattr(edge, "callback_bindings", []):
                    if binding.get("callback") != target_name:
                        continue
                    target_module_cg = self.project_cg.modules.get(module)
                    if (target_module_cg is None
                            or target_name not in target_module_cg.functions):
                        continue
                    callback_args = normalize_source(binding.get("args"))
                    if not isinstance(callback_args, TupleSource):
                        continue
                    if param_index >= len(callback_args.items):
                        continue
                    arg_source = callback_args.items[param_index]
                    key = (caller_module, edge.call_lineno,
                           edge.call_col_offset, source_display(arg_source))
                    self._append_parameter_argument(
                        found, seen, key, caller_module, arg_source)

    ## Collect arguments from exact project call-graph targets.
    def _collect_project_edge_arguments(
            self, module, scope_name, parameter, param_index, tracers,
            found, seen, prefer_protocol_shape, prefer_iterable_elements,
            receiver_class_filter):
        cg = getattr(self, "project_cg", None)
        if cg is None:
            return
        target_cg = cg.modules.get(module)
        target_summary = (
            target_cg.functions.get(scope_name)
            if target_cg is not None else None)
        if target_summary is None:
            target_summary = (
                target_cg.functions.get(scope_name.rsplit(".", 1)[-1])
                if target_cg is not None else None)
        for caller_module, module_cg in cg.modules.items():
            caller_tracer = tracers.get(caller_module)
            for edge in module_cg.edges:
                if not self._edge_targets_local_function(
                        edge, caller_module, module, scope_name,
                        caller_tracer, tracers,
                        allow_inherited_dispatch=True):
                    continue
                if (receiver_class_filter is not None
                        and not self._edge_receiver_may_have_class(
                            edge, caller_module, receiver_class_filter,
                            tracers)):
                    continue
                edge_args = self._edge_parameter_sources(
                    edge, target_summary, parameter, param_index,
                    prefer_protocol_shape=prefer_protocol_shape,
                    prefer_iterable_elements=prefer_iterable_elements)
                if edge_args is None:
                    continue
                for arg_source in edge_args:
                    key = (
                        caller_module,
                        edge.call_lineno,
                        edge.call_col_offset,
                        source_display(arg_source),
                    )
                    self._append_parameter_argument(
                        found, seen, key, caller_module, arg_source)

    ## Check the narrow standard-library callback contract supported above.
    #  @param edge Candidate call edge.
    #  @return True only for multiprocessing.Pool.map(...).
    def _is_multiprocessing_map_edge(self, edge, tracer=None):
        if (not isinstance(getattr(edge, "callee_name", None), str)
                or not edge.callee_name.endswith(".map")):
            return False
        receiver = normalize_source(getattr(edge, "receiver_source", None))
        if not isinstance(receiver, CallResult):
            return False
        if receiver.callee == "multiprocessing":
            return True
        if tracer is None or not isinstance(receiver.callee, str):
            return False
        root = receiver.callee.split(".", 1)[0]
        return normalize_source(
            tracer.symbols.direct.get(root)) == "multiprocessing"

    ## Check the narrow standard-library Process callback contract.
    #  @param edge Candidate call edge.
    #  @param tracer Caller-module analyzer, used for direct imports.
    #  @return True only for multiprocessing.Process.
    def _is_multiprocessing_process_edge(self, edge, tracer=None):
        callee_name = getattr(edge, "callee_name", None)
        if callee_name == "multiprocessing.Process":
            return True
        if callee_name != "Process" or tracer is None:
            return False
        return (getattr(tracer, "import_from_symbols", {}).get("Process")
                == "multiprocessing.Process")

    ## Select sources supplied to one parameter from a resolved call edge.
    #  @param edge Call graph edge.
    #  @param summary Callee function signature summary.
    #  @param parameter Target parameter name.
    #  @param param_index Position in the flattened parameter list.
    #  @param prefer_protocol_shape Use independent PythonShape evidence.
    #  @param prefer_iterable_elements Use preserved iterable element evidence.
    #  @return List of sources, or None when the edge cannot bind safely.
    def _edge_parameter_sources(self, edge, summary, parameter, param_index,
                                prefer_protocol_shape=False,
                                prefer_iterable_elements=False):
        if summary is None:
            return None
        ordinary_args = edge.arg_sources
        if prefer_iterable_elements:
            ordinary_args = getattr(edge, "iterable_arg_sources", {})
        elif prefer_protocol_shape:
            ordinary_args = {
                "pos": dict(edge.arg_sources.get("pos", {})),
                "kw": dict(edge.arg_sources.get("kw", {})),
            }
            protocol_args = getattr(edge, "protocol_arg_sources", {})
            ordinary_args["pos"].update(protocol_args.get("pos", {}))
            ordinary_args["kw"].update(protocol_args.get("kw", {}))
        return bind_parameter_sources(
            summary.signature, parameter, ordinary_args.get('pos', {}),
            ordinary_args.get('kw', {}), getattr(edge, 'star_arg_sources', {}),
            getattr(edge, 'star_kwarg_sources', []), ContainerItem, OWNERSHIP_BINDING)

    ## Collect the selected item of a variadic parameter from each exact
    #  project-local call edge.
    #  @param module Defining module of the variadic parameter.
    #  @param pack_source ParameterSource naming *args or **kwargs.
    #  @param index Integer position or keyword name.
    #  @param tracers Per-module analyzers.
    #  @return List of (caller module, selected source) tuples.
    def _parameter_pack_item_arguments(self, module, pack_source, index,
                                       tracers):
        if not isinstance(pack_source, ParameterSource):
            return []
        cg = getattr(self, "project_cg", None)
        target_cg = cg.modules.get(module) if cg is not None else None
        if target_cg is None:
            return []
        summary = target_cg.functions.get(pack_source.scope)
        if summary is None:
            summary = target_cg.functions.get(
                pack_source.scope.rsplit(".", 1)[-1])
        if summary is None or pack_source.name not in summary.params:
            return []
        param_index = summary.params.index(pack_source.name)
        found = []
        seen = set()
        for caller_module, caller_cg in cg.modules.items():
            caller_tracer = tracers.get(caller_module)
            for edge in caller_cg.edges:
                if not self._edge_targets_local_function(
                        edge, caller_module, module, pack_source.scope,
                        caller_tracer, tracers):
                    continue
                selected = self._edge_pack_item_source(
                    edge, summary, pack_source.name, index)
                if selected is None:
                    continue
                key = (caller_module, edge.call_lineno,
                       edge.call_col_offset, source_display(selected))
                if key in seen:
                    continue
                seen.add(key)
                found.append((caller_module, selected))
        return found

    ## Select one item from a variadic parameter on one call edge.
    #  @param edge Call graph edge.
    #  @param summary Callee signature summary.
    #  @param parameter Variadic parameter name.
    #  @param index Integer position or keyword name.
    #  @return Selected source or None when the edge is ambiguous.
    def _edge_pack_item_source(self, edge, summary, parameter, index):
        if parameter == summary.vararg:
            if not isinstance(index, int):
                return None
            positional_params = list(
                getattr(summary, "positional_params", []))
            actual_index = len(positional_params) + index
            positional = edge.arg_sources.get("pos", {})
            if actual_index in positional:
                return positional[actual_index]
            star_item = self._star_positional_item_source(
                edge, summary, actual_index)
            return star_item
        if parameter == summary.kwarg:
            if not isinstance(index, str):
                return None
            keyword_args = edge.arg_sources.get("kw", {})
            if index in keyword_args:
                positional_params = set(
                    getattr(summary, "positional_params", []))
                keyword_only = set(
                    getattr(summary, "keyword_only_params", []))
                if index not in positional_params | keyword_only:
                    return keyword_args[index]
            star_kwargs = getattr(edge, "star_kwarg_sources", [])
            if len(star_kwargs) == 1:
                return ContainerItem(star_kwargs[0], index)
        return None

    ## Return whether a CallEdge targets one specific local callable.
    #
    #  Handles module functions, class constructors, local methods, and
    #  statically enumerated callback-table values. Ambiguous local method
    #  receivers are accepted only as possible local targets; owner
    #  convergence still happens across every collected argument source.
    #
    #  @param edge Project call-graph edge.
    #  @param caller_module Module containing the call.
    #  @param target_module Defining module.
    #  @param scope_name Qualified target function name.
    #  @param caller_tracer Analyzer for caller module.
    #  @param tracers Dict of module name to analyzer.
    #  @param allow_inherited_dispatch Match inherited and overridden methods
    #  for parameter-flow analysis.
    #  @return True when the edge resolves to the target function.
    def _edge_targets_local_function(self, edge, caller_module,
                                     target_module, scope_name,
                                     caller_tracer, tracers,
                                     allow_inherited_dispatch=False):
        mapping_targets = getattr(edge, "mapping_targets", None)
        if mapping_targets is not None:
            return FunctionId(target_module, scope_name) in mapping_targets
        target = self._local_target_metadata(target_module, scope_name)
        if target is None:
            return False
        target_cg, class_name, target_name, is_constructor, is_method = target
        if ("." in scope_name and not (is_constructor or is_method)):
            return (caller_module == target_module
                    and normalize_source(edge.callee_source) == scope_name)

        callable_name = class_name if is_constructor else target_name
        if (not is_method
                and self._explicit_callable_source_matches(
                    edge, callable_name, class_name, is_constructor)):
            return True
        if (is_method and target_name == "__call__"
                and self._callable_instance_targets_method(
                    edge, caller_module, target_module, class_name,
                    caller_tracer, tracers)):
            return True

        callee_name = getattr(edge, "callee_name", "") or ""
        if (not callee_name
                or callee_name.rsplit(".", 1)[-1] != callable_name):
            return False
        if is_method:
            return self._method_edge_targets_local_function(
                edge, caller_module, target_module, class_name,
                target_cg, tracers, allow_inherited_dispatch)
        return self._plain_edge_targets_local_function(
            edge, caller_module, target_module, callable_name,
            is_constructor, caller_tracer, tracers)

    ## Describe one local function, constructor, or method target.
    #  @return Target metadata tuple, or None when its module is unavailable.
    def _local_target_metadata(self, target_module, scope_name):
        cg = getattr(self, "project_cg", None)
        target_cg = cg.modules.get(target_module) if cg is not None else None
        if target_cg is None:
            return None
        parts = scope_name.split(".")
        class_name = parts[-2] if len(parts) >= 2 else ""
        target_name = parts[-1]
        is_constructor = (
            target_name == "__init__"
            and class_name in target_cg.classes)
        is_method = (
            not is_constructor
            and class_name in target_cg.classes
            and target_name in target_cg.classes[class_name].methods)
        return (target_cg, class_name, target_name,
                is_constructor, is_method)

    ## Match an exact callable source retained on the edge.
    def _explicit_callable_source_matches(
            self, edge, callable_name, class_name, is_constructor):
        callback_sources = normalize_source(
            getattr(edge, "callee_source", None))
        if isinstance(callback_sources, SourceSet):
            callback_values = callback_sources.sources
        else:
            callback_values = [callback_sources]
        for candidate in callback_values:
            candidate = normalize_source(candidate)
            if (isinstance(candidate, str)
                    and candidate.rsplit(".", 1)[-1] == callable_name
                    and (not is_constructor
                         or not isinstance(
                             normalize_source(edge.callee), InstanceMethod))
                    and (not is_constructor or class_name == callable_name)):
                return True
        return False

    ## Match a local callable instance to its __call__ implementation.
    def _callable_instance_targets_method(
            self, edge, caller_module, target_module, class_name,
            caller_tracer, tracers):
        callable_classes = self._local_callable_class_candidates(
            caller_module,
            getattr(edge, "callee", None),
            caller_tracer,
            tracers,
            display_name=getattr(edge, "callee_name", ""),
        )
        return any(
            self._local_class_is_or_derives(
                candidate_module, candidate_class,
                target_module, class_name, tracers)
            for candidate_module, candidate_class in callable_classes
        )

    ## Match one edge to a local method target.
    def _method_edge_targets_local_function(
            self, edge, caller_module, target_module, class_name,
            target_cg, tracers, allow_inherited_dispatch):
        callee = normalize_source(edge.callee)
        if (edge.receiver_source is None
                and not isinstance(callee, InstanceMethod)):
            return False
        if (isinstance(callee, InstanceMethod)
                and isinstance(callee.receiver, str)
                and callee.receiver in target_cg.classes):
            receiver_classes = self._local_class_candidates(
                caller_module, edge.receiver_source, tracers)
            if not receiver_classes:
                local_identity = self._local_class_from_source(
                    caller_module, callee.receiver)
                if local_identity is not None:
                    receiver_classes = [local_identity]
            if receiver_classes:
                if not allow_inherited_dispatch:
                    return (target_module, class_name) in receiver_classes
                if edge.receiver_source == "self":
                    return any(
                        self._local_class_is_or_derives(
                            target_module, class_name,
                            candidate_module, candidate_class, tracers)
                        for candidate_module, candidate_class
                        in receiver_classes
                    )
                return any(
                    self._local_class_is_or_derives(
                        candidate_module, candidate_class,
                        target_module, class_name, tracers)
                    for candidate_module, candidate_class in receiver_classes
                )
        receiver_class = self._resolve_local_class_identity(
            caller_module, edge.receiver_source, tracers)
        if receiver_class is not None:
            if allow_inherited_dispatch:
                return self._local_class_is_or_derives(
                    receiver_class[0], receiver_class[1],
                    target_module, class_name, tracers)
            return receiver_class == (target_module, class_name)
        if edge.receiver_source == "self":
            return self._self_receiver_targets_method(
                edge, caller_module, target_module, class_name,
                tracers, allow_inherited_dispatch)
        if callee in ("local", "self"):
            return True
        receiver_candidates = self._argument_owner_candidates(
            caller_module, edge.receiver_source, tracers)
        return self._dedupe_list(receiver_candidates) == ["local"]

    ## Match a self receiver against its enclosing local class.
    def _self_receiver_targets_method(
            self, edge, caller_module, target_module, class_name,
            tracers, allow_inherited_dispatch):
        caller_parts = edge.caller.qualname.rsplit(".", 1)
        caller_class = caller_parts[0] if len(caller_parts) == 2 else ""
        caller_cg = self.project_cg.modules.get(caller_module)
        if caller_cg is None or caller_class not in caller_cg.classes:
            return False
        if allow_inherited_dispatch:
            return self._local_class_is_or_derives(
                target_module, class_name,
                caller_module, caller_class, tracers)
        return caller_module == target_module and caller_class == class_name

    ## Match one edge to a local function or constructor target.
    def _plain_edge_targets_local_function(
            self, edge, caller_module, target_module, callable_name,
            is_constructor, caller_tracer, tracers):
        if not is_constructor and edge.receiver_source is not None:
            receiver_class = self._resolve_local_class_identity(
                caller_module, edge.receiver_source, tracers)
            if receiver_class is not None or edge.receiver_source == "self":
                return False

        callee_name = edge.callee_name
        first = callee_name.split(".", 1)[0]
        if caller_tracer is not None:
            imported = caller_tracer.import_from_symbols.get(first)
            if imported:
                return imported == target_module + "." + callable_name
            direct = normalize_source(
                caller_tracer.symbols.direct.get(first))
            if isinstance(direct, str) and direct not in (
                    "", "local", "python", "unknown"):
                if direct == target_module:
                    return True
                if direct.endswith("." + callable_name):
                    return direct == target_module + "." + callable_name
                if not self.is_local(direct):
                    return False

        if caller_module == target_module and callee_name == callable_name:
            return True
        definitions = self._get_definition_index().defining_modules(
            callable_name,
            kind="class" if is_constructor else "function")
        return len(definitions) == 1 and definitions[0] == target_module
