## @package pcresolve.project_result_binding
#  Bounded call, callback, iterator, and method-result binding passes.

from .ownership_contracts import _has_result_owner_contract
from .sources import (
    CallResult, ContainerItem, ContainerIter, DerivedResult, InstanceMethod,
    ParameterSource, SourceSet, UnknownSource, make_source_set,
    normalize_source,
)


_SKIP_RESULT = object()

## Check whether a source contains explicit project return evidence.
#  This distinguishes a receiver propagated through a local return or tuple
#  binding from an independently verified external result contract.  The
#  latter may classify the current call, but it must not rewrite unrelated
#  downstream records as new call-graph evidence.
#  @param source Source value to inspect.
#  @param _seen Recursion guard for nested source objects.
#  @return True when the source contains a return-origin SourceSet.
def _has_return_provenance(source, _seen=None):
    source = normalize_source(source)
    if source is None:
        return False
    if _seen is None:
        _seen = set()
    marker = id(source)
    if marker in _seen:
        return False
    _seen.add(marker)
    if isinstance(source, SourceSet):
        if source.origin == "return":
            return True
        return any(_has_return_provenance(item, _seen)
                   for item in source.sources)
    if isinstance(source, CallResult):
        return _has_return_provenance(source.result_source, _seen)
    if isinstance(source, DerivedResult):
        return any(_has_return_provenance(item, _seen)
                   for item in source.sources)
    if isinstance(source, InstanceMethod):
        return _has_return_provenance(source.receiver, _seen)
    return False


## Project result-binding passes mixed into ProjectAnalyzer.
class ProjectResultBindingMixin:
    ## Select one positional element from a function return summary.
    #
    #  SourceSet represents alternative return branches, so every branch must
    #  provide the same positional element. A tuple DerivedResult is the only
    #  aggregate shape consumed here. Other return values remain whole-result
    #  sources and use the existing path.
    #  @param source Return summary source.
    #  @param index Zero-based assignment position.
    #  @return Selected element source, or None when position is unproven.
    def _return_item_source(self, source, index):
        source = normalize_source(source)
        if isinstance(source, SourceSet):
            items = []
            for branch in source.sources:
                item = self._return_item_source(branch, index)
                if item is None:
                    return None
                items.append(item)
            if not items:
                return None
            return make_source_set(items, origin=source.origin or "return")
        if isinstance(source, DerivedResult) and source.kind == "tuple":
            if index < 0 or index >= len(source.sources):
                return None
            return normalize_source(source.sources[index])
        return None

    ## Return whether a summary explicitly describes a positional tuple.
    #  @param source Return summary source.
    #  @return True when every alternative has tuple positional evidence.
    def _is_tuple_return_source(self, source):
        source = normalize_source(source)
        if isinstance(source, SourceSet):
            return bool(source.sources) and all(
                self._is_tuple_return_source(branch)
                for branch in source.sources)
        return isinstance(source, DerivedResult) and source.kind == "tuple"

    ## Return whether one tuple element is concrete enough to replace a
    #  caller binding. Parameter-derived and unresolved elements must stay on
    #  the legacy bounded path, because their owner still depends on a
    #  runtime argument or an external return contract.
    #  @param source Positional tuple element source.
    #  @return True when the source carries usable owner evidence.
    def _is_resolved_return_item(self, source):
        source = normalize_source(source)
        if isinstance(source, SourceSet):
            return bool(source.sources) and all(
                self._is_resolved_return_item(branch)
                for branch in source.sources)
        if isinstance(source, (UnknownSource, DerivedResult)):
            return False
        return source is not None

    ## Check whether a return summary contains an opaque call result.
    #
    #  A call's callable owner is not a contract for the returned object's
    #  owner. Inherited-target fallback therefore must not extend that legacy
    #  inference unless the CallResult carries an explicit result_source.
    #  @param source Function return summary source.
    #  @return True when any branch contains an unqualified CallResult.
    def _has_opaque_call_result(self, source):
        source = normalize_source(source)
        if isinstance(source, SourceSet):
            return any(
                self._has_opaque_call_result(branch)
                for branch in source.sources)
        if isinstance(source, CallResult):
            if source.result_source is None:
                return True
            return self._has_opaque_call_result(source.result_source)
        if isinstance(source, DerivedResult):
            return any(
                self._has_opaque_call_result(branch)
                for branch in source.sources)
        return False

    ## Check whether a return summary is an unresolved receiver method call.
    #
    #  The callable owner of ``self.worker.predict()`` does not establish the
    #  owner of the object returned by ``predict``.  Constructor-style local
    #  factories remain separate because their existing source contract is a
    #  CallResult rather than a parameter-backed InstanceMethod.
    #  @param source Function return summary source.
    #  @return True when a branch returns a parameter-backed method result.
    def _has_unresolved_method_result(self, source):
        source = normalize_source(source)
        if isinstance(source, SourceSet):
            return any(
                self._has_unresolved_method_result(branch)
                for branch in source.sources)
        if isinstance(source, InstanceMethod):
            return bool(source.parameter_scope)
        if isinstance(source, DerivedResult):
            return any(
                self._has_unresolved_method_result(branch)
                for branch in source.sources)
        return False

    ## Preserve exact result calls for assigned project-local methods.
    #  @param tracers Dict of module name to analyzer.
    def _bind_bounded_local_call_results(self, tracers):
        for caller_module, module_cg in self.project_cg.modules.items():
            tracer = tracers.get(caller_module)
            if tracer is None:
                continue
            assignment_edges = self._assigned_call_edges(module_cg)
            for edge in module_cg.edges:
                target_summary = self._bounded_local_result_summary(
                    edge, caller_module, tracer, tracers)
                if target_summary is None:
                    continue
                target, summary = target_summary
                for index, name in enumerate(edge.assigned_to):
                    self._bind_assigned_local_result(
                        module_cg, tracer, edge, target, summary,
                        index, name, assignment_edges)

    ## Index assigned call edges by caller scope and target name.
    #  @param module_cg Module call graph.
    #  @return Ordered assignment-edge mapping.
    def _assigned_call_edges(self, module_cg):
        assignments = {}
        for edge in module_cg.edges:
            for name in edge.assigned_to:
                assignments.setdefault(
                    (edge.caller.qualname, name), []).append(edge)
        for edges in assignments.values():
            edges.sort(key=lambda item: (
                item.call_lineno, item.call_col_offset))
        return assignments

    ## Resolve one assigned edge to a usable local return summary.
    #  @param edge Candidate call edge.
    #  @param caller_module Caller module name.
    #  @param tracer Caller module analyzer.
    #  @param tracers All module analyzers.
    #  @return Pair of target and summary, or None.
    def _bounded_local_result_summary(
            self, edge, caller_module, tracer, tracers):
        if not edge.assigned_to:
            return None
        targets = self._local_edge_targets(edge, caller_module, tracers)
        if len(targets) != 1:
            return None
        target = targets[0]
        summary = self.project_cg.modules[
            target.module].functions.get(target.qualname)
        if summary is None or summary.returns is None:
            return None
        exact_target = self._edge_targets_local_function(
            edge, caller_module, target.module, target.qualname,
            tracer, tracers)
        if (not exact_target
                and self._has_opaque_call_result(summary.returns)):
            return None
        return target, summary

    ## Bind and propagate one assigned name from a local return summary.
    #  @param module_cg Caller module call graph.
    #  @param tracer Caller analyzer.
    #  @param edge Producing call edge.
    #  @param target Resolved local target.
    #  @param summary Resolved target summary.
    #  @param assigned_index Position in a tuple assignment.
    #  @param assigned_name Assigned receiver name.
    #  @param assignment_edges Ordered assignment-edge mapping.
    def _bind_assigned_local_result(
            self, module_cg, tracer, edge, target, summary,
            assigned_index, assigned_name, assignment_edges):
        assigned_edges = assignment_edges.get(
            (edge.caller.qualname, assigned_name), [])
        edge_index = assigned_edges.index(edge)
        next_position = None
        if edge_index + 1 < len(assigned_edges):
            next_edge = assigned_edges[edge_index + 1]
            next_position = (next_edge.call_lineno, next_edge.call_col_offset)
        result_source = self._assigned_result_source(
            edge, summary, assigned_index)
        if result_source is _SKIP_RESULT:
            return
        current = normalize_source(tracer.symbols.direct.get(assigned_name))
        result_call = CallResult(
            target.module + "." + target.qualname,
            display_name=edge.callee_name,
            call_lineno=edge.call_lineno,
            call_col_offset=edge.call_col_offset,
            result_source=result_source)
        current_position = (
            getattr(current, "call_lineno", 0),
            getattr(current, "call_col_offset", 0))
        if (edge_index == len(assigned_edges) - 1
                and (isinstance(current, InstanceMethod)
                     or current_position == (
                         edge.call_lineno, edge.call_col_offset))):
            tracer.symbols.direct[assigned_name] = result_call
        self._rewrite_assigned_result_records(
            tracer, edge, target, assigned_name, current,
            result_call, next_position)
        self._rewrite_assigned_result_edges(
            module_cg, edge, assigned_name, result_call, next_position)

    ## Select the whole or positional result source for one assigned name.
    #  A private sentinel represents an unproven tuple position.
    #  @param edge Producing call edge.
    #  @param summary Target function summary.
    #  @param assigned_index Assignment position.
    #  @return Source, None for whole result, or a private skip sentinel.
    def _assigned_result_source(self, edge, summary, assigned_index):
        if len(edge.assigned_to) <= 1:
            return None
        selected = self._return_item_source(summary.returns, assigned_index)
        if selected is not None and self._is_resolved_return_item(selected):
            return selected
        if self._is_tuple_return_source(summary.returns):
            return _SKIP_RESULT
        return None

    ## Rewrite later API records that read one assigned local result.
    #  @param tracer Caller analyzer.
    #  @param edge Producing call edge.
    #  @param target Resolved local target.
    #  @param assigned_name Assigned receiver name.
    #  @param current Previous direct source.
    #  @param result_call Contextual result source.
    #  @param next_position Next assignment position or None.
    def _rewrite_assigned_result_records(
            self, tracer, edge, target, assigned_name, current,
            result_call, next_position):
        caller_scope = (
            "" if edge.caller.qualname == "<module>"
            else edge.caller.qualname)
        start = (edge.call_lineno, edge.call_col_offset)
        for record in tracer.api_calls:
            func_name = record.get("func_name", "")
            record_base = normalize_source(record.get("base"))
            position = (record.get("lineno", 0), record.get("col_offset", 0))
            if (not self._assigned_receiver_matches(
                    record_base, current, assigned_name, result_call, target)
                    or not func_name.startswith(assigned_name + ".")
                    or record.get("scope_name", "") != caller_scope
                    or position <= start
                    or (next_position is not None
                        and position > next_position)):
                continue
            record["base"] = InstanceMethod(
                result_call, func_name.rsplit(".", 1)[-1])

    ## Check whether a record receiver denotes the assigned result.
    #  @return True when the receiver matches existing bounded evidence.
    def _assigned_receiver_matches(
            self, record_base, current, assigned_name, result_call, target):
        matches = record_base == current
        if isinstance(record_base, InstanceMethod):
            receiver = normalize_source(record_base.receiver)
            if receiver == assigned_name:
                matches = True
            if receiver == current:
                matches = True
            if (isinstance(record_base.receiver, str)
                    and isinstance(result_call.callee, str)):
                matches = (
                    record_base.receiver
                    == result_call.callee.rsplit(".", 1)[-1])
            if (isinstance(current, InstanceMethod)
                    and current.method == record_base.method
                    and current.method
                    == target.qualname.rsplit(".", 1)[-1]):
                matches = True
        return matches

    ## Rewrite later call edges that use one assigned result as receiver.
    #  @param module_cg Caller module call graph.
    #  @param edge Producing call edge.
    #  @param assigned_name Assigned receiver name.
    #  @param result_call Contextual result source.
    #  @param next_position Next assignment position or None.
    def _rewrite_assigned_result_edges(
            self, module_cg, edge, assigned_name,
            result_call, next_position):
        start = (edge.call_lineno, edge.call_col_offset)
        for future_edge in module_cg.edges:
            position = (future_edge.call_lineno, future_edge.call_col_offset)
            if (future_edge.caller != edge.caller
                    or position <= start
                    or (next_position is not None
                        and position > next_position)
                    or not isinstance(future_edge.callee_name, str)
                    or not future_edge.callee_name.startswith(
                        assigned_name + ".")):
                continue
            future_edge.receiver_source = result_call
            if isinstance(future_edge.callee, InstanceMethod):
                future_edge.callee = InstanceMethod(
                    result_call, future_edge.callee.method)
            future_edge.callee_source = result_call
    ## Bind one converged local callback return to a Pool.map result field.
    #
    #  The existing callback edge proves which project function is invoked.
    #  This pass adds the reverse result edge: every callback return branch
    #  must resolve to one owner before calls through a mapped result item are
    #  rewritten. The rewrite ends at the next source-level rebind.
    #  @param tracers Dict of module name to analyzer.
    def _bind_bounded_callback_map_results(self, tracers):
        for caller_module, module_cg in self.project_cg.modules.items():
            tracer = tracers.get(caller_module)
            if tracer is None:
                continue
            for edge in module_cg.edges:
                if (not edge.assigned_to
                        or not self._is_multiprocessing_map_edge(
                            edge, tracer)):
                    continue
                callback_names = self._dedupe_list(
                    getattr(edge, "callback_args", {}).values())
                if len(callback_names) != 1:
                    continue
                callback_summary = module_cg.functions.get(
                    callback_names[0])
                if (callback_summary is None
                        or callback_summary.returns is None):
                    continue
                owners = self._dedupe_list(
                    self._origin_candidates(
                        caller_module, callback_summary.returns, tracers))
                owners = [
                    owner for owner in owners
                    if owner not in (None, "")
                ]
                result_source = callback_summary.returns
                if len(owners) != 1 or owners[0] == "unknown":
                    result_source = UnknownSource(
                        "mixed callback result owners")
                for assigned_name in edge.assigned_to:
                    next_position = self._next_assignment_rebind_position(
                        tracer, module_cg, edge, assigned_name)
                    self._rewrite_mapped_result_records(
                        tracer, edge, assigned_name,
                        result_source, next_position)
                    self._rewrite_mapped_result_edges(
                        module_cg, edge, assigned_name,
                        result_source, next_position)
                    class_name = self._stable_field_assignment_class(
                        tracer, module_cg, edge, assigned_name)
                    if class_name:
                        self._rewrite_class_mapped_result_records(
                            tracer, module_cg, class_name, assigned_name,
                            result_source)
                        self._rewrite_class_mapped_result_edges(
                            module_cg, class_name, assigned_name,
                            result_source)

    ## Return the owning class for one uniquely assigned instance field.
    #  @param tracer Analyzer containing field assignment references.
    #  @param module_cg Caller module call graph.
    #  @param edge Pool.map assignment edge.
    #  @param assigned_name Candidate self-field name.
    #  @return Class name when the field has exactly one assignment, else "".
    def _stable_field_assignment_class(
            self, tracer, module_cg, edge, assigned_name):
        if (not assigned_name.startswith("self.")
                or "." not in edge.caller.qualname):
            return ""
        class_name = edge.caller.qualname.split(".", 1)[0]
        if class_name not in module_cg.classes:
            return ""
        for ref in getattr(tracer, "symbol_refs", []):
            if ref.symbol != assigned_name or ref.kind != "variable":
                continue
            source = normalize_source(ref.source)
            if (not isinstance(source, CallResult)
                    or source.call_lineno != edge.call_lineno
                    or source.call_col_offset != edge.call_col_offset):
                return ""
        for other_edge in module_cg.edges:
            if (other_edge is not edge
                    and assigned_name in other_edge.assigned_to):
                return ""
        return class_name

    ## Find the next source-level assignment to one mapped result binding.
    #  @param tracer Analyzer containing provenance references.
    #  @param module_cg Caller module call graph.
    #  @param edge Current Pool.map call edge.
    #  @param assigned_name Name or self-field receiving the result.
    #  @return Position tuple or None.
    def _next_assignment_rebind_position(
            self, tracer, module_cg, edge, assigned_name):
        current = (edge.call_lineno, edge.call_col_offset)
        scopes = {
            edge.caller.qualname,
            edge.caller.qualname.rsplit(".", 1)[-1],
        }
        candidates = []
        for ref in getattr(tracer, "symbol_refs", []):
            position = (
                getattr(ref, "lineno", 0),
                getattr(ref, "col_offset", 0),
            )
            if (ref.symbol == assigned_name
                    and getattr(ref, "scope_name", "") in scopes
                    and position > current):
                candidates.append(position)
        for future_edge in module_cg.edges:
            position = (
                future_edge.call_lineno,
                future_edge.call_col_offset,
            )
            if (future_edge.caller == edge.caller
                    and assigned_name in future_edge.assigned_to
                    and position > current):
                candidates.append(position)
        return min(candidates) if candidates else None

    ## Return the method suffix following a mapped container item.
    #  @param func_name Callable spelling from an API record or edge.
    #  @param assigned_name Mapped result binding.
    #  @return Empty string for direct item calls, method name for item methods,
    #          or None when the callable is unrelated.
    @staticmethod
    def _mapped_item_method(func_name, assigned_name):
        if (not isinstance(func_name, str)
                or not func_name.startswith(assigned_name + "[")):
            return None
        closing = func_name.find("]", len(assigned_name) + 1)
        if closing < 0:
            return None
        suffix = func_name[closing + 1:]
        if not suffix:
            return ""
        if not suffix.startswith("."):
            return None
        return suffix.rsplit(".", 1)[-1]

    ## Rewrite API records using one bounded mapped-result item source.
    #  @param tracer Caller analyzer.
    #  @param edge Pool.map assignment edge.
    #  @param assigned_name Mapped result binding.
    #  @param result_source Converged callback return summary.
    #  @param next_position Next rebind position or None.
    def _rewrite_mapped_result_records(
            self, tracer, edge, assigned_name, result_source,
            next_position):
        caller_scope = ("" if edge.caller.qualname == "<module>"
                        else edge.caller.qualname.rsplit(".", 1)[-1])
        start = (edge.call_lineno, edge.call_col_offset)
        for record in tracer.api_calls:
            position = (
                record.get("lineno", 0),
                record.get("col_offset", 0),
            )
            method = self._mapped_item_method(
                record.get("func_name", ""), assigned_name)
            if (method is None
                    or record.get("scope_name", "") != caller_scope
                    or position <= start
                    or (next_position is not None
                        and position >= next_position)):
                continue
            record["base"] = (
                result_source if not method
                else InstanceMethod(result_source, method))

    ## Rewrite downstream call edges using a mapped-result item source.
    #  @param module_cg Caller module call graph.
    #  @param edge Pool.map assignment edge.
    #  @param assigned_name Mapped result binding.
    #  @param result_source Converged callback return summary.
    #  @param next_position Next rebind position or None.
    def _rewrite_mapped_result_edges(
            self, module_cg, edge, assigned_name, result_source,
            next_position):
        start = (edge.call_lineno, edge.call_col_offset)
        for future_edge in module_cg.edges:
            position = (
                future_edge.call_lineno,
                future_edge.call_col_offset,
            )
            method = self._mapped_item_method(
                future_edge.callee_name, assigned_name)
            if (method is None
                    or future_edge.caller != edge.caller
                    or position <= start
                    or (next_position is not None
                        and position >= next_position)):
                continue
            source = (
                result_source if not method
                else InstanceMethod(result_source, method))
            future_edge.callee = source
            future_edge.callee_source = source
            if method:
                future_edge.receiver_source = result_source

    ## Resolve the unique class containing one API record's method scope.
    #  @param module_cg Module call graph.
    #  @param scope_name Bare method scope stored on the API record.
    #  @return Class name when unique, otherwise "".
    @staticmethod
    def _record_scope_class(module_cg, scope_name):
        matches = [
            class_name for class_name, summary in module_cg.classes.items()
            if scope_name in summary.methods
        ]
        return matches[0] if len(matches) == 1 else ""

    ## Rewrite mapped field-item records across one proven local class.
    #  @param tracer Caller analyzer.
    #  @param module_cg Caller module call graph.
    #  @param class_name Class with one field assignment.
    #  @param assigned_name Mapped self-field binding.
    #  @param result_source Converged callback return summary.
    def _rewrite_class_mapped_result_records(
            self, tracer, module_cg, class_name, assigned_name,
            result_source):
        for record in tracer.api_calls:
            method = self._mapped_item_method(
                record.get("func_name", ""), assigned_name)
            if (method is None
                    or self._record_scope_class(
                        module_cg, record.get("scope_name", ""))
                    != class_name):
                continue
            record["base"] = (
                result_source if not method
                else InstanceMethod(result_source, method))

    ## Rewrite mapped field-item edges across one proven local class.
    #  @param module_cg Caller module call graph.
    #  @param class_name Class with one field assignment.
    #  @param assigned_name Mapped self-field binding.
    #  @param result_source Converged callback return summary.
    def _rewrite_class_mapped_result_edges(
            self, module_cg, class_name, assigned_name, result_source):
        prefix = class_name + "."
        for edge in module_cg.edges:
            method = self._mapped_item_method(
                edge.callee_name, assigned_name)
            if method is None or not edge.caller.qualname.startswith(prefix):
                continue
            source = (
                result_source if not method
                else InstanceMethod(result_source, method))
            edge.callee = source
            edge.callee_source = source
            if method:
                edge.receiver_source = result_source

    ## Bind a local generator or returned iterable to its exact for-loop.
    #  The binding is bounded by the exact iterator call site and the next
    #  rebind of each loop target. No external return contract is inferred.
    #  @param tracers Dict of module name to analyzer.
    def _bind_bounded_local_iteration_results(self, tracers):
        for caller_module, module_cg in self.project_cg.modules.items():
            tracer = tracers.get(caller_module)
            if tracer is None:
                continue
            for binding in getattr(module_cg, "iteration_bindings", []):
                if binding.caller.module != caller_module:
                    continue
                iterator_edges = [
                    edge for edge in module_cg.edges
                    if edge.caller == binding.caller
                    and edge.call_lineno == binding.call_lineno
                    and edge.call_col_offset == binding.call_col_offset
                    and edge.callee_name == binding.callee_name
                ]
                if len(iterator_edges) != 1:
                    continue
                edge = iterator_edges[0]
                targets = self._local_edge_targets(
                    edge, caller_module, tracers)
                if len(targets) != 1:
                    continue
                summary = self.project_cg.modules[
                    targets[0].module].functions.get(targets[0].qualname)
                if summary is None:
                    continue
                if summary.yields is not None:
                    yield_source = self._substitute_generator_parameters(
                        summary.yields, edge, summary, tracers)
                else:
                    # Preserve the selected call until its returned elements
                    # can be substituted, separately from the container owner.
                    yield_source = ContainerIter(CallResult(
                        edge.callee_source,
                        display_name=edge.callee_name,
                        call_lineno=edge.call_lineno,
                        call_col_offset=edge.call_col_offset,
                        source_module=caller_module))
                if yield_source is None:
                    continue
                for target_name in binding.target_names:
                    next_position = self._next_iteration_rebind_position(
                        module_cg, tracer, binding, target_name)
                    self._rewrite_generator_target_records(
                        tracer, binding, target_name, yield_source,
                        next_position)
                    self._rewrite_generator_target_edges(
                        module_cg, binding, target_name, yield_source,
                        next_position)
                    current = normalize_source(
                        tracer.symbols.direct.get(target_name))
                    if (isinstance(current, CallResult)
                            and current.call_lineno == binding.call_lineno
                            and current.call_col_offset
                            == binding.call_col_offset):
                        tracer.symbols.direct[target_name] = yield_source

    ## Substitute exact call-edge arguments into a local generator yield.
    #
    #  A generator summary may yield one of its own parameters.  The summary
    #  is declaration-level evidence, so it still names the generator's
    #  ParameterSource.  An exact local call edge supplies the concrete source
    #  for that parameter.  This substitution is bounded to one iterator call
    #  site and does not infer any external library return semantics.
    #  @param source Generator yield source or nested source IR.
    #  @param edge Exact call edge for the iterator expression.
    #  @param summary Callee function summary containing parameter metadata.
    #  @return Substituted source, or None when the parameter is ambiguous.
    def _substitute_generator_parameters(
            self, source, edge, summary, tracers, _seen=None):
        source = normalize_source(source)
        if isinstance(source, ParameterSource):
            if source.scope != summary.id.qualname:
                nested = self._nested_generator_parameter_argument(
                    source, edge, summary, tracers, _seen)
                return source if nested is None else nested
            parameter_index = summary.params.index(source.name) \
                if source.name in summary.params else None
            if parameter_index is None:
                return None
            arguments = self._edge_parameter_sources(
                edge, summary, source.name, parameter_index,
                prefer_protocol_shape=True)
            if arguments is None or len(arguments) != 1:
                return None
            argument = normalize_source(arguments[0])
            if source.attributes or source.derived:
                # The current bounded generator contract preserves direct
                # parameter yields. Attribute and derived yields need a
                # separate source-composition contract.
                return None
            return argument
        if isinstance(source, SourceSet):
            substituted = []
            for item in source.sources:
                item_source = self._substitute_generator_parameters(
                    item, edge, summary, tracers, _seen)
                if item_source is None:
                    return None
                substituted.append(item_source)
            return make_source_set(substituted, origin=source.origin)
        if isinstance(source, InstanceMethod):
            receiver = self._substitute_generator_parameters(
                source.receiver, edge, summary, tracers, _seen)
            if receiver is None:
                return None
            return InstanceMethod(
                receiver, source.method, source.parameter_scope,
                source.parameter_name)
        if isinstance(source, ContainerItem):
            container = self._substitute_generator_parameters(
                source.container, edge, summary, tracers, _seen)
            if container is None:
                return None
            return ContainerItem(container, source.index)
        if isinstance(source, ContainerIter):
            container = self._substitute_generator_parameters(
                source.container, edge, summary, tracers, _seen)
            if container is None:
                return None
            return ContainerIter(container)
        if isinstance(source, CallResult):
            callee = self._substitute_generator_parameters(
                source.callee, edge, summary, tracers, _seen)
            if callee is None:
                return None
            result_source = source.result_source
            if result_source is not None:
                result_source = self._substitute_generator_parameters(
                    result_source, edge, summary, tracers, _seen)
                if result_source is None:
                    return None
            return CallResult(
                callee,
                source.display_name,
                source.call_lineno,
                source.call_col_offset,
                source.source_module,
                result_source)
        if isinstance(source, DerivedResult):
            operands = []
            for item in source.sources:
                item_source = self._substitute_generator_parameters(
                    item, edge, summary, tracers, _seen)
                if item_source is None:
                    return None
                operands.append(item_source)
            return DerivedResult(source.kind, tuple(operands), source.attribute)
        return source

    ## Resolve a parameter inherited through one local yield-from edge.
    #
    #  For ``outer(value): yield from inner(value)``, the return summary of
    #  outer may still contain ``ParameterSource('inner', 'value')``.  Follow
    #  that exact local edge once, then let the caller's edge resolve the
    #  resulting outer parameter.  Ambiguous targets remain unresolved.
    #  @param source Nested generator ParameterSource.
    #  @param edge Outer iterator call edge.
    #  @param summary Current generator summary.
    #  @param tracers Per-module analyzers.
    #  @param _seen Recursion guard.
    #  @return Substituted source, or None when no unique local edge exists.
    def _nested_generator_parameter_argument(
            self, source, edge, summary, tracers, _seen=None):
        seen = set(_seen or set())
        key = (summary.id.module, summary.id.qualname,
               source.scope, source.name)
        if key in seen:
            return None
        seen.add(key)
        module = summary.id.module
        module_cg = self.project_cg.modules.get(module)
        if module_cg is None:
            return None
        nested_edges = []
        nested_summary = None
        for nested_edge in module_cg.edges:
            if nested_edge.caller.qualname != summary.id.qualname:
                continue
            targets = self._local_edge_targets(
                nested_edge, module, tracers)
            matching = [
                target for target in targets
                if target.qualname == source.scope
            ]
            if len(matching) != 1:
                continue
            candidate = module_cg.functions.get(source.scope)
            if candidate is None:
                candidate = self.project_cg.modules[
                    matching[0].module].functions.get(matching[0].qualname)
            if candidate is None or source.name not in candidate.params:
                continue
            nested_edges.append((nested_edge, candidate))
            nested_summary = candidate
        if len(nested_edges) != 1 or nested_summary is None:
            return None
        parameter_index = nested_summary.params.index(source.name)
        arguments = self._edge_parameter_sources(
            nested_edges[0][0], nested_summary, source.name,
            parameter_index, prefer_protocol_shape=True)
        if arguments is None or len(arguments) != 1:
            return None
        return self._substitute_generator_parameters(
            arguments[0], edge, summary, tracers, seen)

    ## Find the next source-level rebind of one loop target.
    #  @param module_cg Module call graph.
    #  @param binding Current iteration binding.
    #  @param target_name Loop target name.
    #  @return Position tuple or None.
    def _next_iteration_rebind_position(self, module_cg, tracer, binding,
                                        target_name):
        current = (binding.call_lineno, binding.call_col_offset)
        candidates = []
        for edge in module_cg.edges:
            if edge.caller != binding.caller or target_name not in (
                    edge.assigned_to or []):
                continue
            position = (edge.call_lineno, edge.call_col_offset)
            if position > current:
                candidates.append(position)
        for other in getattr(module_cg, "iteration_bindings", []):
            if other is binding or other.caller != binding.caller:
                continue
            if target_name not in other.target_names:
                continue
            position = (other.call_lineno, other.call_col_offset)
            if position > current:
                candidates.append(position)
        caller_scope = binding.caller.qualname
        caller_short_scope = caller_scope.rsplit(".", 1)[-1]
        for ref in getattr(tracer, "symbol_refs", []):
            if ref.symbol != target_name:
                continue
            ref_scope = getattr(ref, "scope_name", "")
            if ref_scope not in ("", caller_scope, caller_short_scope):
                continue
            position = (getattr(ref, "lineno", 0),
                        getattr(ref, "col_offset", 0))
            if position > current:
                candidates.append(position)
        return min(candidates) if candidates else None

    ## Rewrite API call records whose receiver is one generator target.
    #  @param tracer Analyzer for the caller module.
    #  @param binding Iteration binding.
    #  @param target_name Loop target name.
    #  @param yield_source Source yielded by the target function.
    #  @param next_position Next rebind position, if any.
    def _rewrite_generator_target_records(
            self, tracer, binding, target_name, yield_source,
            next_position):
        caller_scope = ("" if binding.caller.qualname == "<module>"
                        else binding.caller.qualname)
        start = (binding.call_lineno, binding.call_col_offset)
        for record in tracer.api_calls:
            position = (record.get("lineno", 0),
                        record.get("col_offset", 0))
            func_name = record.get("func_name", "")
            if (record.get("scope_name", "") != caller_scope
                    or position <= start
                    or (next_position is not None
                        and position > next_position)
                    or not func_name.startswith(target_name + ".")):
                continue
            record["base"] = InstanceMethod(
                yield_source, func_name.rsplit(".", 1)[-1])

    ## Rewrite future call edges whose receiver is one generator target.
    #  @param module_cg Module call graph.
    #  @param binding Iteration binding.
    #  @param target_name Loop target name.
    #  @param yield_source Source yielded by the target function.
    #  @param next_position Next rebind position, if any.
    def _rewrite_generator_target_edges(
            self, module_cg, binding, target_name, yield_source,
            next_position):
        start = (binding.call_lineno, binding.call_col_offset)
        for edge in module_cg.edges:
            position = (edge.call_lineno, edge.call_col_offset)
            if (edge.caller != binding.caller
                    or position <= start
                    or (next_position is not None
                        and position > next_position)
                    or not edge.callee_name.startswith(target_name + ".")):
                continue
            edge.receiver_source = yield_source
            edge.callee = InstanceMethod(
                yield_source, edge.callee_name.rsplit(".", 1)[-1])
            edge.callee_source = edge.callee

    ## Propagate proven receivers through assigned method calls.
    #  @param tracers Dict of module name to analyzer.
    def _bind_proven_result_method_results(self, tracers):
        for module, module_cg in self.project_cg.modules.items():
            tracer = tracers.get(module)
            if tracer is None:
                continue
            edges = sorted(
                module_cg.edges,
                key=lambda edge: (
                    edge.caller.qualname,
                    edge.call_lineno,
                    edge.call_col_offset))
            flow = {}
            for edge in edges:
                if not self._bind_proven_result_edge(
                        module, tracer, edge, tracers, flow):
                    self._clear_assigned_result_flow(edge, flow)

    ## Bind one method edge when its receiver has one proven external owner.
    #  @param module Caller module name.
    #  @param tracer Caller module analyzer.
    #  @param edge Candidate method edge.
    #  @param tracers All module analyzers.
    #  @param flow Mutable scope/name result mapping.
    #  @return True when assigned result flow remains valid.
    def _bind_proven_result_edge(
            self, module, tracer, edge, tracers, flow):
        if not isinstance(edge.callee_name, str):
            return False
        root, separator, _ = edge.callee_name.partition(".")
        if not separator:
            return False
        receiver = normalize_source(
            flow.get((edge.caller.qualname, root)))
        if receiver is None:
            receiver = normalize_source(edge.receiver_source)
        if (not isinstance(receiver, CallResult)
                or receiver.result_source is None):
            return False
        origin_module = module
        if isinstance(receiver.callee, str) and "." in receiver.callee:
            candidate = receiver.callee.rsplit(".", 1)[0]
            if candidate in tracers:
                origin_module = candidate
        owners = self._origin_candidates(
            origin_module, receiver.result_source, tracers)
        if (len(owners) != 1
                or owners[0] in ("local", "python", "unknown", "")
                or not _has_return_provenance(receiver.result_source)):
            return False
        records = self._result_method_records(tracer, edge, root)
        if not records:
            return False
        method_name = max(
            (record.get("func_name", "") for record in records),
            key=len).rsplit(".", 1)[-1]
        method_source = InstanceMethod(receiver, method_name)
        edge.receiver_source = receiver
        edge.callee = method_source
        edge.callee_source = method_source
        for record in records:
            method = record.get("func_name", "").rsplit(".", 1)[-1]
            record["base"] = InstanceMethod(receiver, method)
        if not edge.assigned_to or not _has_result_owner_contract(method_name):
            return False
        result_call = CallResult(
            method_source,
            display_name=edge.callee_name,
            call_lineno=edge.call_lineno,
            call_col_offset=edge.call_col_offset,
            result_source=DerivedResult(
                "method_result", (method_source,), method_name))
        for name in edge.assigned_to:
            flow[(edge.caller.qualname, name)] = result_call
            tracer.symbols.direct[name] = result_call
        return True

    ## Return call records located at one receiver-method edge.
    #  @param tracer Caller module analyzer.
    #  @param edge Candidate call edge.
    #  @param root Receiver root name.
    #  @return Matching API-call records.
    def _result_method_records(self, tracer, edge, root):
        scope = ("" if edge.caller.qualname == "<module>"
                 else edge.caller.qualname)
        return [
            record for record in tracer.api_calls
            if record.get("lineno") == edge.call_lineno
            and record.get("col_offset") == edge.call_col_offset
            and record.get("scope_name", "") == scope
            and record.get("func_name", "").startswith(root + ".")]

    ## Remove assigned names from bounded method-result flow.
    #  @param edge Edge that ends or invalidates result flow.
    #  @param flow Mutable scope/name result mapping.
    def _clear_assigned_result_flow(self, edge, flow):
        for name in edge.assigned_to:
            flow.pop((edge.caller.qualname, name), None)
