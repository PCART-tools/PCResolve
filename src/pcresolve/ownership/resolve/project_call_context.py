## @package pcresolve.ownership.resolve.project_call_context
#  Resolve project call contexts.
#
#
#  Exact project call targets, bounded contexts, and parameter binding.
#  精确解析项目调用目标、有界调用上下文和参数绑定。



from pcresolve.ownership.call_graph import FunctionId
from pcresolve.facts.call_resolution import CallContext
from pcresolve.facts.program_facts import (
    bind_parameter_sources, starred_item_source,
    CONTEXT_BINDING, OWNERSHIP_BINDING,
)
from pcresolve.facts.return_resolution import CallBinding, first_bound_value
from pcresolve.ownership.ownership_model import OwnershipCallableIndex, bounded_ownership_query, build_ownership_definition_index, build_ownership_edge_index
from pcresolve.ownership.resolve.target_metadata import TargetMetadataMixin
from pcresolve.ownership.sources import (
    CallResult, ContainerItem, DerivedResult, InstanceMethod, ParameterSource,
    SourceSet, TupleSource, UnknownSource, normalize_source, source_display,
)


_NO_BOUNDED_CANDIDATES = object()


## Project call-context and argument-binding behavior mixed into ProjectAnalyzer.
## 混入 ProjectAnalyzer 的项目调用上下文和参数绑定逻辑。
class ProjectCallContextMixin(TargetMetadataMixin):
    ## Adapt this generation's ownership summaries to the shared name index.
    ## 将当前代归属摘要适配到共享名称索引。
    #  Logical keys and mutable source payloads retain their ownership meaning.
    #  A normal analysis collects a new ProjectCallGraph before resolution.
    #
    #  @return Internal candidate index; not a public call-graph result.
    def _get_ownership_definition_index(self):
        graph = self.project_cg
        generation = graph.version
        run = self._ownership_run
        cached = (run.definition_index if run is not None
                  else getattr(self, '_initial_definition_index', None))
        if cached is None or cached.graph is not graph or cached.generation != generation:
            cached = build_ownership_definition_index(graph, self._local_target_metadata)
            if run is not None:
                run.definition_index = cached
            else:
                self._initial_definition_index = cached
        return cached

    ## Expose the definition records cached for the current call graph generation.
    ## 暴露当前调用图代所缓存的定义记录。
    #
    #  @return Definition index backing ownership candidate lookups.
    def _get_definition_index(self):
        return self._get_ownership_definition_index().definitions

    ## Select possible definitions without inspecting unrelated receivers.
    ## 选择可能的定义，不检查无关接收者。
    #
    #  @param edge Call edge to resolve.
    #  @param caller_module Optional module used to narrow method candidates.
    #  @return Definitions in their original collection order.
    def _edge_target_candidates(self, edge, caller_module=None):
        index = self._get_ownership_definition_index()
        names = self._edge_callable_names(edge)
        ordinals = set()
        for name in names:
            ordinals.update(index.target_names.get(name, ()))
        ordinals.update(self._callable_method_candidates(edge, caller_module))
        return tuple(index.definitions.records[ordinal] for ordinal in sorted(ordinals))

    ## Discard callable facts after edge or module-binding changes.
    ## 调用边或模块绑定变化后丢弃可调用对象事实。
    #
    #  @return None.
    def _invalidate_callable_lookup(self):
        if self._ownership_run is not None:
            self._ownership_run.callable_index = None
        else:
            self._initial_callable_index = None

    ## Initialize static callable facts for this binding generation.
    ## 为当前绑定版本初始化静态可调用对象事实。
    #
    #  @return None.
    def _ensure_callable_lookup(self):
        graph = self.project_cg
        generation = graph.version
        run = self._ownership_run
        cached = (run.callable_index if run is not None
                  else getattr(self, '_initial_callable_index', None))
        if cached is None or cached.graph is not graph or cached.generation != generation:
            cached = OwnershipCallableIndex(graph, generation)
            if run is not None:
                run.callable_index = cached
            else:
                self._initial_callable_index = cached
        return cached

    ## Reuse only callable classes independent of recursive parameter proofs.
    ## 仅复用不依赖递归参数证明的可调用类候选。
    #
    #  @param edge Project call edge whose callee is inspected.
    #  @param module Caller module used for source lookup.
    #  @param tracers Module-to-analyzer mapping.
    #  @return Class identities, or None when parameter evidence is required.
    def _static_callable_classes(self, edge, module, tracers):
        ## Detect receiver sources that require query-specific parameter evidence.
        ## 检查接收者来源是否需要查询专属的参数证据。
        #
        #  @param source Candidate receiver source.
        #  @return True when source depends on a receiver parameter.
        def dynamic(source):
            source = normalize_source(source)
            if isinstance(source, SourceSet):
                return any(dynamic(item) for item in source.sources)
            return (isinstance(source, InstanceMethod) and source.parameter_scope
                    and source.receiver == source.parameter_name)

        if dynamic(edge.callee):
            return None
        index = self._ensure_callable_lookup()
        key = (module, id(edge))
        cached = index.static_classes.get(key)
        if (cached is None or cached[1] is not edge.callee
                or cached[2] != edge.callee_name):
            classes = self._local_callable_class_candidates(
                module, edge.callee, tracers.get(module), tracers,
                display_name=edge.callee_name)
            # Retain the edge itself, preventing identity reuse for temporary edges.
            cached = (edge, edge.callee, edge.callee_name, tuple(classes))
            index.static_classes[key] = cached
        return cached[3]

    ## Select callable-instance methods using source facts, not bounded proofs.
    ## 使用源码事实选择可调用实例方法，不把候选当作有界证明。
    #  Unknown parameter sources and inherited classes retain every candidate.
    #
    #  @param edge Project call edge to inspect.
    #  @param module Caller module, if known.
    #  @return Definition ordinals requiring the existing exact target check.
    def _callable_method_candidates(self, edge, module):
        index = self._get_ownership_definition_index()
        ordinals = index.target_names.get('__call__', ())
        if not ordinals or module is None:
            return ordinals
        tracers = self._ownership_run.program.module_tracers
        classes = self._static_callable_classes(edge, module, tracers)
        if classes is None:
            return ordinals
        if any(tracers.get(owner) is not None
               and tracers[owner].class_bases.get(name)
               for owner, name in classes):
            return ordinals
        identities = set(classes)
        return tuple(ordinal for ordinal in ordinals
                     if (index.definitions.records[ordinal].module,
                         self._local_target_metadata(
                             index.definitions.records[ordinal].module,
                             index.definitions.records[ordinal].qualname)[1])
                     in identities)

    ## Index possible incoming callable-instance edges in original order.
    ## 按原始顺序索引可能指向可调用实例的调用边。
    #
    #  @return Target identity to edge ordinals; exact matching stays query-local.
    def _get_callable_reverse_lookup(self):
        edge_lookup = self._get_edge_lookup()
        edges, _, _, _ = edge_lookup
        index = self._ensure_callable_lookup()
        if index.indexed_edges is not edge_lookup:
            index.indexed_edges = edge_lookup
            index.reverse_lookup = None
        if index.reverse_lookup is None:
            lookup = {}
            for edge_ordinal, (module, edge) in enumerate(edges):
                for ordinal in self._callable_method_candidates(edge, module):
                    record = self._get_definition_index().records[ordinal]
                    lookup.setdefault((record.module, record.qualname), set()).add(edge_ordinal)
            index.reverse_lookup = lookup
        return index.reverse_lookup

    ## Update syntactic edge indexes after a callable-source rewrite.
    ## 可调用来源改写后更新语法调用边索引。
    #
    #  @param edge Rewritten edge, or None to discard all indexed facts.
    #  @return None; resolution results themselves are never cached here.
    def _invalidate_edge_lookup(self, edge=None):
        self._invalidate_callable_lookup()
        run = self._ownership_run
        cached = (run.edge_index if run is not None
                  else getattr(self, '_initial_edge_index', None))
        if edge is None or cached is None or cached.graph is not self.project_cg:
            self._set_edge_index(None)
            return
        ordinal = cached.ordinals.get(id(edge))
        if ordinal is None:
            self._set_edge_index(None)
            return
        position = (edge.caller.qualname, edge.call_lineno, edge.call_col_offset,
                    getattr(edge, 'mapping_targets', None) is not None)
        if cached.positions[ordinal] != position:
            self._set_edge_index(None)
            return
        names = cached.data[1]
        previous = cached.edge_names[ordinal]
        current = self._edge_callable_names(edge)
        for name in previous - current:
            names[name].discard(ordinal)
        for name in current - previous:
            names.setdefault(name, set()).add(ordinal)
        cached.edge_names[ordinal] = current

    ## Store the ownership edge index for the current analysis generation.
    ## 保存当前分析代的归属调用边索引。
    #
    #  @param index Edge index to cache, or None to clear the cached index.
    #  @return None
    def _set_edge_index(self, index):
        if self._ownership_run is not None:
            self._ownership_run.edge_index = index
        else:
            self._initial_edge_index = index

    ## Index call spellings and source locations for the current edge facts.
    ## 为当前调用边事实建立名称及源码位置索引。
    #
    #  @return Ordered edges, name buckets, mapping edges, and location buckets.
    def _get_ownership_edge_index(self):
        graph = self.project_cg
        generation = graph.version
        run = self._ownership_run
        cached = (run.edge_index if run is not None
                  else getattr(self, '_initial_edge_index', None))
        if cached is None or cached.graph is not graph or cached.generation != generation:
            cached = build_ownership_edge_index(graph, self._edge_callable_names)
            self._set_edge_index(cached)
        return cached

    ## Expose the cached edge lookup buckets for the current call graph.
    ## 暴露当前调用图缓存的调用边查找桶。
    #
    #  @return Ordered edges, name buckets, mapping edges, and location buckets.
    def _get_edge_lookup(self):
        return self._get_ownership_edge_index().data

    ## Return one lexical caller's edges in original collection order.
    ## 按原始收集顺序返回一个词法调用者的调用边。
    #
    #  @param module Caller module.
    #  @param scope Caller qualified name.
    #  @return Ordered edge tuple, retaining every spelling and candidate.
    def _call_edges_in_scope(self, module, scope):
        index = self._get_ownership_edge_index()
        return tuple(index.scopes.get((module, scope), ()))

    ## Select candidate callback-contract edges by accepted callable spellings.
    ## 根据回调契约接受的名称筛选候选调用边。
    #
    #  @param names Terminal callable spellings accepted by the contract.
    #  @return Ordered caller-module and edge pairs, requiring contract checks.
    def _call_edges_named(self, *names):
        edges, lookup, _, _ = self._get_edge_lookup()
        ordinals = set()
        for name in names:
            ordinals.update(lookup.get(name, ()))
        return tuple(edges[ordinal] for ordinal in sorted(ordinals))

    ## Select possible callers of one definition, retaining exact dispatch checks.
    ## 筛选某个定义的潜在调用者，并保留精确分派检查。
    #
    #  @param module Target module.
    #  @param scope_name Target lexical qualified name.
    #  @return Ordered caller-module and edge pairs.
    def _target_call_edges(self, module, scope_name):
        edges, names, mapped, _ = self._get_edge_lookup()
        metadata = self._local_target_metadata(module, scope_name)
        if metadata is None:
            return tuple(edges[ordinal] for ordinal in mapped)
        _, class_name, name, constructor, method = metadata
        callable_name = class_name if constructor else name
        ordinals = set(names.get(callable_name, ()))
        ordinals.update(mapped)
        if method and name == '__call__':
            ordinals.update(self._get_callable_reverse_lookup().get((module, scope_name), ()))
        return tuple(edges[ordinal] for ordinal in sorted(ordinals))

    ## Find all project-local functions reached by one call edge.
    ## 查找一条调用边可达的所有项目内函数。
    #
    #  @param edge Call edge to resolve.
    #  @param caller_module Module containing the edge.
    #  @param tracers Dict of module name to analyzer.
    #  @return Deduplicated project-local targets in stable candidate order.
    #  @return List of matching FunctionId values.
    def _local_edge_targets(self, edge, caller_module, tracers):
        if getattr(edge, "mapping_targets", None) is not None:
            if not edge.mapping_targets_complete:
                return []
            return list(edge.mapping_targets)
        targets = []
        caller_tracer = tracers.get(caller_module)
        candidates = self._edge_target_candidates(edge, caller_module)
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
    ## 移除被派生类本地实现遮蔽的祖先方法。
    #
    #  Multiple-inheritance siblings remain separate candidates because this
    #  bounded resolver does not claim a complete Python MRO. A linear local
    #  inheritance chain, however, has one unambiguous nearest implementation.
    #
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
    ## 解析显式局部可调用来源集合中的每个分支。
    #
    #  This deliberately rejects inferred method-name candidates. Multiple
    #  targets are safe to converge only when the call edge itself retains
    #  each exact project-local callable selected by source control flow.
    #
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
    ## 根据一个精确调用点位置构建所有项目内调用上下文。
    #
    #  Multiple contexts are retained for a statically enumerated callable
    #  branch. Their result owners are converged by the caller.
    #
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
        edges = self._get_edge_lookup()[3].get(
            (caller_module, call_lineno, call_col_offset), ())
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
    ## 根据调用点位置构建唯一的有界调用上下文。
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
    ## 读取有界调用上下文中传给指定形参的实参来源。
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
    ## 从星号实参中解析一个位置形参对应的元素。
    #
    #  @param edge Call graph edge.
    #  @param summary Callee signature summary.
    #  @param index Zero-based positional parameter index.
    #  @return ContainerItem selecting the pack item, or None.
    def _star_positional_item_source(self, edge, summary, index):
        return starred_item_source(getattr(edge, 'star_arg_sources', {}), index, ContainerItem)

    ## Resolve one selected item from a local variadic parameter under a
    ## 在有界调用上下文中解析局部可变参数的一个选定元素。
    #  bounded call context.
    #
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
    ## 解析方法返回摘要所引用的构造函数参数。
    #
    #  For Holder.expose() returning the value stored by Holder.__init__,
    #  use the exact receiver constructor edge. No class-name or library-name
    #  table is involved.
    #
    #  @param context Current method-call context.
    #  @param source Constructor ParameterSource.
    #  @param tracers Dict of module name to analyzer.
    #  @param _seen Active bounded-source recursion keys.
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
    ## 在一个精确的局部调用上下文中求值来源。
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

        # Resolve aggregate and parameter evidence before falling back to the
        # context-independent ownership candidates.
        # 先解析聚合和参数证据，再回退到与上下文无关的归属候选。
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
    ## 解析 SourceSet、DerivedResult 和容器聚合来源。
    #
    #  @param source_module Module where the source was recorded.
    #  @param source Structured source to resolve.
    #  @param context Current bounded call context.
    #  @param tracers Module-to-analyzer mapping.
    #  @param seen Active bounded-source recursion keys.
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
    ## 在有界上下文中解析结构化容器选取。
    #
    #  @param source_module Module where the selection was recorded.
    #  @param source Container item source.
    #  @param context Current bounded call context.
    #  @param tracers Module-to-analyzer mapping.
    #  @param seen Active bounded-source recursion keys.
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
    ## 沿有界调用链替换显式 ParameterSource。
    #
    #  @param source_module Module where the parameter source was recorded.
    #  @param source Explicit parameter source.
    #  @param context Current bounded call context, if available.
    #  @param tracers Module-to-analyzer mapping.
    #  @param seen Active bounded-source recursion keys.
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
    ## 沿有界调用链替换旧格式的字符串参数来源。
    #
    #  @param source Legacy parameter name.
    #  @param context Current bounded call context, if available.
    #  @param tracers Module-to-analyzer mapping.
    #  @param seen Active bounded-source recursion keys.
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
    ## 在精确的有界上下文中解析一个 CallResult。
    #
    #  @param source_module Module where the call result was recorded.
    #  @param source Call result to resolve.
    #  @param context Current bounded call context, if available.
    #  @param tracers Module-to-analyzer mapping.
    #  @param seen Active bounded-source recursion keys.
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
    ## 使用精确调用点替换解析局部调用结果。
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
    ## 从精确的局部元组返回调用中解析一个位置元素。
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
    ## 汇总有界候选，避免跨归属猜测。
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
    ## 查找包含有界归属导入证据的模块。
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
    ## 收集传递给一个局部函数形参的所有实参来源。
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
    ## 在保留跨来源身份的同时添加一个实参来源。
    #
    #  @param found Mutable list collecting argument pairs.
    #  @param seen Mutable set of already recorded physical call keys.
    #  @param key Stable identity key for this argument occurrence.
    #  @param caller_module Module containing the call site.
    #  @param source Argument source to append.
    #  @return None.
    def _append_parameter_argument(self, found, seen, key,
                                   caller_module, source):
        if key in seen:
            return
        seen.add(key)
        found.append((caller_module, source))

    ## Collect explicit single-file parameterization facts.
    ## 收集单文件分析显式记录的参数化事实。
    #
    #  @param module Module containing the parameterized call.
    #  @param scope_name Qualified function or method name.
    #  @param parameter Target parameter name.
    #  @param tracer Analyzer for the defining module.
    #  @param found Mutable list collecting argument pairs.
    #  @param seen Mutable set deduplicating call sites.
    #  @return None.
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
    ## 收集旧式单文件调用点参数事实。
    #
    #  @param module Target function's defining module.
    #  @param scope_name Target function's qualified name.
    #  @param param_index Target parameter's positional index.
    #  @param tracer Analyzer for the defining module.
    #  @param found Mutable list collecting argument pairs.
    #  @param seen Mutable set deduplicating call sites.
    #  @param prefer_protocol_shape Select protocol-specific argument evidence.
    #  @param prefer_iterable_elements Select iterable element evidence.
    #  @param receiver_class_filter Optional required local receiver class.
    #  @return None.
    ## 收集旧式单文件调用点参数事实。
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
    ## 收集受支持的 multiprocessing.Pool.map 回调实参。
    #
    #  @param scope_name Qualified callback function name.
    #  @param tracers Module-to-analyzer mapping.
    #  @param found Mutable list collecting argument pairs.
    #  @param seen Mutable set deduplicating call sites.
    #  @return None.
    def _collect_pool_map_arguments(self, scope_name, tracers, found, seen):
        target_name = scope_name.rsplit(".", 1)[-1]
        for caller_module, edge in self._call_edges_named('map'):
            caller_tracer = tracers.get(caller_module)
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
    ## 收集受支持的 multiprocessing.Process 回调实参。
    #
    #  @param module Callback function's defining module.
    #  @param scope_name Qualified callback function name.
    #  @param param_index Callback parameter's positional index.
    #  @param tracers Module-to-analyzer mapping.
    #  @param found Mutable list collecting argument pairs.
    #  @param seen Mutable set deduplicating call sites.
    #  @return None.
    def _collect_process_callback_arguments(
            self, module, scope_name, param_index, tracers, found, seen):
        target_name = scope_name.rsplit(".", 1)[-1]
        for caller_module, edge in self._call_edges_named('Process'):
            caller_tracer = tracers.get(caller_module)
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
    ## 从精确的项目调用图目标收集实参来源。
    #
    #  @param module Target function's defining module.
    #  @param scope_name Target qualified function name.
    #  @param parameter Target parameter name.
    #  @param param_index Positional index of the target parameter.
    #  @param tracers Module-to-analyzer mapping.
    #  @param found Mutable list collecting argument pairs.
    #  @param seen Mutable set deduplicating call sites.
    #  @param prefer_protocol_shape Select protocol-specific argument evidence.
    #  @param prefer_iterable_elements Select element sources for iterable inputs.
    #  @param receiver_class_filter Optional required local receiver class.
    #  @return None.
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
        for caller_module, edge in self._target_call_edges(module, scope_name):
            caller_tracer = tracers.get(caller_module)
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
    ## 检查上述支持的受限标准库回调契约。
    #
    #  @param edge Candidate call edge.
    #  @param tracer Caller-module analyzer, used to resolve receiver imports.
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
    ## 检查受支持的受限标准库 Process 回调契约。
    #
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
    ## 从已解析的调用边中选择传给指定形参的来源。
    #
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
    ## 从每条精确调用边收集可变参数中的选定元素。
    #  project-local call edge.
    #
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
        for caller_module, edge in self._target_call_edges(module, pack_source.scope):
            caller_tracer = tracers.get(caller_module)
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
    ## 从一条调用边的可变参数中选择一个元素。
    #
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
    ## 判断调用边是否指向指定的局部可调用对象。
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
    @bounded_ownership_query(lambda: False)
    def _edge_targets_local_function(self, edge, caller_module,
                                     target_module, scope_name,
                                     caller_tracer, tracers,
                                     allow_inherited_dispatch=False):
        # Receiver provenance can request parameter arguments or return
        # contexts that re-enter this exact target query before their own
        # source guards are installed. A cycle supplies no target evidence.
        key = (id(edge), caller_module, target_module, scope_name,
               allow_inherited_dispatch)
        if key in self._edge_target_in_progress:
            return False
        self._edge_target_in_progress.add(key)
        try:
            return self._unguarded_edge_targets_local_function(
                edge, caller_module, target_module, scope_name,
                caller_tracer, tracers, allow_inherited_dispatch)
        finally:
            self._edge_target_in_progress.remove(key)

    ## Match a call target while the receiver-resolution guard is held.
    ## 在接收者解析保护生效时匹配调用目标。
    #
    #  @param edge Project call-graph edge.
    #  @param caller_module Module containing the call.
    #  @param target_module Defining module.
    #  @param scope_name Qualified target function name.
    #  @param caller_tracer Analyzer for caller module.
    #  @param tracers Dict of module name to analyzer.
    #  @param allow_inherited_dispatch Include inherited method candidates.
    #  @return True when available evidence resolves the edge to the target.
    def _unguarded_edge_targets_local_function(
            self, edge, caller_module, target_module, scope_name,
            caller_tracer, tracers, allow_inherited_dispatch=False):
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

    ## Match an exact callable source retained on the edge.
    ## 匹配调用边上保留的精确可调用来源。
    #
    #  @param edge Project call-graph edge.
    #  @param callable_name Expected terminal callable name.
    #  @param class_name Local class name for constructor matching.
    #  @param is_constructor Whether the target is a constructor.
    #  @return True when an explicit callee source matches the target.
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
    ## 将局部可调用实例匹配到其 __call__ 实现。
    #
    #  @param edge Call edge carrying the callable instance.
    #  @param caller_module Module containing the call edge.
    #  @param target_module Module defining the candidate class.
    #  @param class_name Candidate local callable class.
    #  @param caller_tracer Analyzer for the caller module.
    #  @param tracers Module-to-analyzer mapping.
    #  @return True when a candidate class matches or derives from the target.
    def _callable_instance_targets_method(
            self, edge, caller_module, target_module, class_name,
            caller_tracer, tracers):
        callable_classes = self._static_callable_classes(edge, caller_module, tracers)
        if callable_classes is None:
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
    ## 将一条调用边匹配到局部方法目标。
    #
    #  @param edge Project call-graph edge.
    #  @param caller_module Module containing the call.
    #  @param target_module Module defining the method.
    #  @param class_name Target class name.
    #  @param target_cg Target module call graph.
    #  @param tracers Module-to-analyzer mapping.
    #  @param allow_inherited_dispatch Whether inherited targets are included.
    #  @return True when receiver and method evidence match the target.
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
    ## 将 self 接收者与其所在的局部类匹配。
    #
    #  @param edge Project call-graph edge.
    #  @param caller_module Module containing the caller.
    #  @param target_module Module defining the candidate method.
    #  @param class_name Candidate target class.
    #  @param tracers Module-to-analyzer mapping.
    #  @param allow_inherited_dispatch Whether derived classes may dispatch here.
    #  @return True when the enclosing class reaches the target method.
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
    ## 将一条调用边匹配到局部函数或构造函数目标。
    #
    #  @param edge Project call-graph edge.
    #  @param caller_module Module containing the call.
    #  @param target_module Module defining the target.
    #  @param callable_name Target function or class name.
    #  @param is_constructor Whether the target is a constructor.
    #  @param caller_tracer Analyzer for import and symbol evidence.
    #  @param tracers Module-to-analyzer mapping.
    #  @return True when available source and receiver facts match the target.
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
