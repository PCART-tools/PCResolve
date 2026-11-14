## @package pcresolve.flow.runtime.analysis_run
#  Per-run analysis, call-context propagation and summary merging.
#  单次运行分析、调用上下文传播和摘要合并。

import ast

import copy

from dataclasses import asdict, replace

from pcresolve.flow.model.results import FlowAnalysis, FlowCall, FunctionRef, _matches

from pcresolve.flow.transfer.summary import _Summary

from pcresolve.flow.transfer.environment import (
    merge_environments as _merge_env, merge_result_sources as _merge_result_sources,
)

from pcresolve.runtime.limits import AnalysisBudget

from pcresolve.facts.call_resolution import DefinitionRecord, DefinitionIndex, CallContext

from pcresolve.facts.scope_facts import (FLOW_SCOPE, function_scope_facts,
                          statement_scope_facts, transitive_captured_names)

from pcresolve.flow.proofs.namespaces.source._source_dependencies import publish as publish_source_dependencies

from pcresolve.flow.proofs.namespaces.source._source_dependencies import validate as validate_source_dependencies

from pcresolve.flow.proofs.callables._constructor_entry import binding as constructor_entry_binding

from pcresolve.flow.proofs.callables._fresh_receiver import (method_binding as fresh_method_binding,
                              super_method_binding as fresh_super_method_binding,
                              incoming_origin as fresh_incoming_origin)

from pcresolve.flow.proofs.callables.dispatch.entry_alias import reference as source_entry_alias

from pcresolve.flow.proofs.callables.dispatch.conditional_constructor import supports_entry as conditional_constructor_entry



## Deduplicate values while retaining their first occurrence order.
## 去重并保留值首次出现的顺序。
#
#  @param values Iterable of comparable values.
#  @return List of unique values in input order.
def _unique(values):
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result

## Run selected entry analyses and merge explicit flow summaries.
## 执行选定入口分析并合并显式数据流摘要。
class FlowRunMixin:

    ## Collect transitive lexical captures from known enclosing bindings.
    ## 从已知外层绑定中收集传递性词法捕获。
    #
    #  @param ref Source function identity.
    #  @param node Function or lambda AST.
    #  @return Captured names in stable order.
    def _captures(self, ref, node):
        if ref in self._capture_name_cache:
            return list(self._capture_name_cache[ref])
        outer = set()
        parent = ref.qualname.rpartition('.')[0]
        while parent:
            definitions = self._definition_index.find(ref.module, parent)
            definition = definitions[0][1] if definitions else None
            if definition:
                outer.update(self._scope_facts(definition).bound)
            parent = parent.rpartition('.')[0]
        names = transitive_captured_names(node, outer)
        self._capture_name_cache[ref] = names
        return list(names)

    ## Find indexed modules reachable through static import bindings.
    ## 查找通过静态导入绑定可达的已索引模块。
    #
    #  @param entry_module Starting module name.
    #  @return Set of reachable module names.
    def _reachable_modules(self, entry_module):
        known = set(self.imports)
        known.update(boundary.get('module') for boundary in self.index_boundaries
                     if boundary.get('module'))
        reachable = set()
        pending = [entry_module]
        while pending:
            module = pending.pop()
            if module in reachable:
                continue
            reachable.add(module)
            for imported in self.imports.get(module, {}).values():
                target = next((candidate for candidate in sorted(
                    known, key=len, reverse=True)
                    if imported == candidate or imported.startswith(candidate + '.')), None)
                if target is not None and target not in reachable:
                    pending.append(target)
        return reachable

    ## Identify parameters without visible reads when reflection is absent.
    ## 在没有可见反射能力时识别未被读取的参数。
    #
    #  @param node Function or lambda AST.
    #  @return Parameter records, or empty list when reflection prevents proof.
    def _unreferenced_parameters(self, node):
        arguments = node.args
        parameters = (arguments.posonlyargs + arguments.args + arguments.kwonlyargs +
                      ([arguments.vararg] if arguments.vararg else []) +
                      ([arguments.kwarg] if arguments.kwarg else []))
        statements = [node.body] if isinstance(node, ast.Lambda) else node.body
        body = [child for statement in statements for child in ast.walk(statement)]
        if any((isinstance(child, ast.Name) and child.id in
                ('locals', 'vars', 'eval', 'exec')) or
               (isinstance(child, ast.Attribute) and child.attr in
                ('f_locals', 'currentframe', '_getframe')) for child in body):
            return []
        loaded = {child.id for child in body
                  if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)}
        return [{'kind': 'parameter', 'name': parameter.arg, 'element_path': []}
                for parameter in parameters if parameter.arg not in loaded]

    ## Analyze reachable summaries up to a bounded number of call edges.
    ## 在有限调用边深度内分析可达摘要。
    #
    #  @param entry FunctionRef identifying a function or source class invocation.
    #  @param max_depth Number of call-edge layers, at least one.
    #  @param max_functions Maximum distinct function summaries.
    #  @param max_call_contexts Maximum traversed call edges.
    #  @param conditional_source_state Retain source-class lookup under explicit state predicates.
    #  @param max_class_effect_steps Maximum class-effect fact steps.
    #  @return FlowAnalysis snapshot; cutoffs are explicit boundaries.
    def analyze(self, entry, max_depth=1, max_functions=500, max_call_contexts=2000,
                conditional_source_state=False, max_class_effect_steps=8000):
        if type(conditional_source_state) is not bool:
            raise ValueError('conditional_source_state must be bool')
        if type(max_class_effect_steps) is not int or max_class_effect_steps < 1:
            raise ValueError('max_class_effect_steps must be a positive integer')
        self._conditional_source_state = conditional_source_state
        if min(max_depth, max_functions, max_call_contexts) < 1:
            raise ValueError('Depth and budgets must be positive')
        self._analysis_budget = (AnalysisBudget(self.analysis_limits)
                                 if self.analysis_limits is not None else None)
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint(force=True)
        self._index()
        self._fact_functions, self._fact_calls = max_functions, max_call_contexts
        self._object_fact_functions = max_functions
        self._object_fact_steps = max_call_contexts
        self._effect_fact_functions = max_functions
        self._effect_fact_steps = max_call_contexts
        self._class_effect_fact_steps = max_class_effect_steps
        # Resolve entry aliases, constructors and inherited methods only with unique evidence.
        # 仅在证据唯一时解析入口别名、构造函数和继承方法。
        matches = [(r, n) for r, n in self.definitions if _matches(r, entry)]
        entry_binding = None
        entry_alias = None
        if not matches and not entry.file_path and not entry.lineno:
            qualified = entry.module + '.' + entry.qualname
            imported = self._resolve_import_binding(qualified)
            if imported is not None:
                matches = [imported]
            elif self._stable_import_name(qualified):
                imported_class = self._definition_index.resolve_qualified(
                    [qualified], self.imports, kind='class',
                    qualified_guard=self._stable_import_name)
                if imported_class is not None:
                    target = self._constructor_target(imported_class)
                    if target is not None:
                        matches = [target]
                        entry_binding = constructor_entry_binding(self, imported_class, target)
        if not matches:
            classes = [(r, n) for r, n in self.classes if _matches(r, entry)]
            if len(classes) == 1:
                target = self._constructor_target(classes[0])
                if target is not None:
                    matches = [target]
                    entry_binding = constructor_entry_binding(self, classes[0], target)
        if not matches:
            alias = source_entry_alias(self, entry)
            if alias is not None:
                target, entry_alias = alias
                matches = [target]
        if not matches and not entry.lineno and '.' in entry.qualname:
            owner, _, method = entry.qualname.rpartition('.')
            inherited = self._inherited_method(entry.module, owner, method)
            if inherited is not None:
                matches = [inherited]
        if len(matches) != 1:
            raise ValueError('Entry must identify exactly one available definition')
        if conditional_source_state and (
                entry_binding is not None and entry_binding['status'] != 'source_bound'
                or entry_binding is None and not conditional_constructor_entry(matches[0][1])):
            raise ValueError('Conditional state analysis requires a source class binding or bounded constructor query')
        result = FlowAnalysis(matches[0][0], {'source_files': sorted(self.files), 'sha256': dict(self.hashes),
                              'import_roots': list(self.roots), 'max_depth': max_depth,
                              'max_class_effect_steps': max_class_effect_steps,
                              'module_global_rebindings': self._module_global_rebindings(),
                              'return_summaries': copy.deepcopy(self.return_summaries),
                              'parameter_shapes': copy.deepcopy(self.parameter_shapes),
                              'coverage': 'explicit value dependencies and limited local container effects; no general heap or path feasibility proof'})
        if conditional_source_state:
            result.inputs['conditional_source_state'] = True
        if entry_alias is not None:
            result.inputs['entry_alias'] = entry_alias
            result.boundaries.append({'reason': 'source_entry_alias',
                'function': asdict(result.entry), 'boundary_kind': 'assumption',
                'assumptions': copy.deepcopy(entry_alias['assumptions'])})
        elif entry_binding is None:
            declarations = self._module_global_declarations(result.entry)
            if declarations:
                result.boundaries.append({'reason': 'module_callable_binding_unconfirmed',
                    'function': asdict(result.entry), 'nominal_target': asdict(result.entry),
                    'lookup_scope': 'module_entry', 'boundary_kind': 'uncertainty',
                    'declarations': [{'file_path': result.entry.file_path,
                        'lineno': statement.lineno, 'col_offset': statement.col_offset,
                        'end_lineno': statement.end_lineno, 'end_col_offset': statement.end_col_offset}
                        for statement in declarations]})
        # Keep source failures as boundaries even when their relation is uncertain.
        # 即使与入口的关系不确定，也将源码失败保留为边界。
        reachable_modules = self._reachable_modules(matches[0][0].module)
        unreferenced = self._unreferenced_parameters(matches[0][1])
        for boundary in self.index_boundaries:
            record = copy.deepcopy(boundary)
            related = record.get('module') in reachable_modules
            record.update(
                affected_scope='unknown' if related else 'none',
                affected_values=[],
                unaffected_values=copy.deepcopy(unreferenced) if related else [],
                entry_relation='possible' if related else 'unrelated',
                relation_basis='static_import_reachability')
            result.boundaries.append(record)
        context = CallContext(matches[0][0].module, matches[0][0], None)
        if entry_binding is not None:
            result.inputs['entry_binding'] = copy.deepcopy(entry_binding)
            result.boundaries.append({'function': asdict(result.entry),
                'reason': 'source_constructor_entry_binding' if entry_binding['status']
                          == 'source_bound' else 'constructor_entry_unconfirmed',
                'boundary_kind': 'assumption' if entry_binding['status'] == 'source_bound'
                                 else 'limitation',
                'assumptions': copy.deepcopy(entry_binding['assumptions']),
                'issues': copy.deepcopy(entry_binding['issues'])})
            if entry_binding['status'] != 'source_bound':
                if self._analysis_budget is not None:
                    self._analysis_budget.checkpoint(force=True)
                publish_source_dependencies(self, result)
                return result
            if entry_binding['phase'] == '__new__':
                result.boundaries.append({'function': asdict(result.entry),
                    'reason': 'constructor_initialization_unmodeled', 'phase': '__init__'})
        self._walk(result, matches[0], max_depth, context, max_functions, max_call_contexts)
        publish_source_dependencies(self, result)
        result.boundaries = _unique(result.boundaries)
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint(force=True)
        return result

    ## Expand one call context, retaining recursion and budget cutoffs as boundaries.
    ## 展开单个调用上下文，将递归和预算截断保留为边界。
    #
    #  @param result Mutable analysis snapshot.
    #  @param definition Source function identity and AST pair.
    #  @param depth Remaining call-edge depth.
    #  @param context Current call context.
    #  @param max_functions Maximum context summaries.
    #  @param max_calls Maximum traversed calls.
    #  @return None
    def _walk(self, result, definition, depth, context, max_functions, max_calls):
        if self._analysis_budget is not None:
            self._analysis_budget.checkpoint(force=True)
        ref, node = definition
        if ref in context.ancestors:
            result.boundaries.append({'function': asdict(ref), 'reason': 'recursion'})
            return
        receiver_class = self._receiver_class(definition, context.edge)
        incoming = self._incoming_facts(definition, context.edge)
        entry_binding = result.inputs.get('entry_binding') if context.edge is None else None
        if entry_binding is not None and entry_binding['status'] == 'source_bound':
            parameter = entry_binding['implicit_binding']['parameter']
            identity = copy.deepcopy(entry_binding['receiver_class'])
            if entry_binding['phase'] == '__new__':
                receiver_class = FunctionRef(**identity)
                incoming[parameter] = [{'class_type': identity,
                    'source_class_origin': {'basis': 'source_symbol', 'class': identity,
                        'evidence': [copy.deepcopy(entry_binding['definition_evidence'])],
                        'call_context': []}}]
            else:
                incoming[parameter] = [{'instance_type': identity}]
                if entry_binding.get('fresh_receiver_origin'):
                    incoming[parameter][0]['fresh_receiver_origin'] = copy.deepcopy(
                        entry_binding['fresh_receiver_origin'])
        # Cache by incoming context so different argument facts do not share summaries.
        # 按传入上下文缓存，避免不同实参事实共用摘要。
        key = (ref, receiver_class, context.edge.id if context.edge else None,
               repr(incoming))
        if key in self._context_summaries:
            calls = self._context_summaries[key]
        else:
            if (len(self._context_summaries) >= max_functions
                    or self._context_call_count >= max_calls):
                result.boundaries.append({'function': asdict(ref), 'reason': 'budget_exceeded'})
                return
            scratch = FlowAnalysis(ref, {})
            selected = self._selected_definition(definition, incoming)
            summary = _Summary(self, scratch, ref, selected[1],
                               max_calls - self._context_call_count, receiver_class,
                               incoming)
            activation = self.definition_conditions.get(ref, ())
            if activation:
                summary.conditions = _unique(summary.conditions + list(copy.deepcopy(activation)))
                scratch.boundaries.append({'function': asdict(ref),
                    'reason': 'conditional_definition_unconfirmed',
                    'conditions': copy.deepcopy(activation), 'affected_scope': 'unknown',
                    'affected_values': []})
            summary.run()
            calls = summary.calls
            if context.edge is not None:
                for call in calls:
                    call.analysis_contexts.append({
                        'incoming_call_id': context.edge.id,
                        'parameter_facts': copy.deepcopy(incoming),
                        'target': asdict(call.target) if call.target else None,
                        'target_candidates': copy.deepcopy(call.target_candidates),
                        'target_status': call.target_status,
                        'binding_status': call.binding_status,
                        'argument_sources': copy.deepcopy(call.argument_sources),
                        'callable_sources': copy.deepcopy(call.callable_sources)})
                    call.analysis_contexts[-1].update(
                        result_sources=copy.deepcopy(call.result_sources),
                        capture_bindings=copy.deepcopy(call.capture_bindings),
                        effects=copy.deepcopy(call.effects),
                        callable_instance_evidence=copy.deepcopy(call.callable_instance_evidence),
                        conditional_returns=copy.deepcopy(call.conditional_returns),
                        class_method_bindings=copy.deepcopy(call.class_method_bindings),
                        class_metadata_bindings=copy.deepcopy(call.class_metadata_bindings),
                        class_read_bindings=copy.deepcopy(call.class_read_bindings),
                        conditional_source_bindings=copy.deepcopy(call.conditional_source_bindings),
                        candidate_paths=copy.deepcopy(call.candidate_paths),
                        constructor_bindings=copy.deepcopy(call.constructor_bindings),
                        instance_method_bindings=copy.deepcopy(call.instance_method_bindings),
                        implicit_protocol=copy.deepcopy(call.implicit_protocol),
                        conditions=copy.deepcopy(call.conditions if self._conditional_source_state
                            else getattr(selected[1], '_flow_conditions', [])))
            self._context_summaries[key] = calls
            self._context_call_count += len(calls)
            self._merge_summary(result, scratch)
        for call in calls:
            if call.target is None:
                if call.target_status not in ('python_protocol', 'local_container_protocol',
                                              'builtin_allocation'):
                    result.boundaries.append({'call_id': call.id, 'callee_name': call.callee_name,
                                              'reason': call.target_status})
            elif depth > 1:
                result.boundaries = [b for b in result.boundaries if not (b.get('call_id') == call.id and b['reason'] == 'depth_limit')]
                target = next(d for d in self._definition_index.find(call.target.module, call.target.qualname)
                              if d[0] == call.target)
                child = CallContext(call.caller.module, call.target, call, context)
                self._walk(result, target, depth - 1, child, max_functions, max_calls)
            else:
                result.boundaries.append({'call_id': call.id, 'reason': 'depth_limit'})

    ## Prepare parameter and capture facts from an incoming call edge.
    ## 从传入调用边准备参数和捕获事实。
    #
    #  @param definition Target source function definition.
    #  @param edge Incoming call record, or None at the entry.
    #  @return Incoming facts keyed by local name.
    def _incoming_facts(self, definition, edge):
        if edge is None or edge.binding_status == 'invalid':
            return {}
        normal_binding = edge.binding_status != 'complete'
        fresh_super = [fact for fact in edge.instance_method_bindings
                       if fact.get('kind') == 'fresh_source_super_method'
                       and fact.get('status') == 'source_bound'
                       and fact.get('target') == asdict(definition[0])
                       and edge.target_status == 'super_method']
        fresh_instance = [fact for fact in edge.instance_method_bindings
                          if fact.get('kind') == 'fresh_source_instance_method'
                          and fact.get('status') == 'source_bound'
                          and fact.get('target') == asdict(definition[0])
                          and fact.get('call_id') == edge.id]
        seeded_receiver = {}
        if len(fresh_instance) == 1:
            parameters = definition[1].args.posonlyargs + definition[1].args.args
            fact = fresh_instance[0]
            origin = fact.get('origin')
            identity = fact.get('receiver_class')
            receiver_values = edge.receiver_sources
            receiver_records = [record for record in edge.parameter_bindings
                if record.get('argument') == {'receiver': True}
                and record.get('parameter') == (parameters[0].arg if parameters else None)
                and record.get('status') == 'exact']
            if (parameters and isinstance(origin, dict) and identity == origin.get('allocation', {}).get(
                    'receiver_class') and len(receiver_records) == 1 and receiver_values
                    and all(value.get('fresh_receiver_origin') == origin
                        and value.get('instance_type') in (None, identity)
                        and value.get('relation') == 'direct'
                        and not any(value.get(flag) for flag in (
                            'projection', 'output_path', 'attribute_provenance',
                            'import_modified', 'import_incomplete'))
                        for value in receiver_values)):
                receiver = {'instance_type': copy.deepcopy(identity),
                    'fresh_receiver_origin': fresh_incoming_origin(fact, parameters[0].arg)}
                mutations = [value.get('class_lookup_mutations', []) for value in receiver_values]
                if all(item == mutations[0] for item in mutations) and mutations[0]:
                    receiver['class_lookup_mutations'] = copy.deepcopy(mutations[0])
                conditions = [value.get('conditions', []) for value in receiver_values]
                if all(item == conditions[0] for item in conditions) and conditions[0]:
                    receiver['conditions'] = copy.deepcopy(conditions[0])
                seeded_receiver[parameters[0].arg] = [receiver]
        if normal_binding and (not edge.binding_issues or any(
                issue.get('kind') != 'dynamic_expansion' for issue in edge.binding_issues)):
            if len(fresh_super) == 1:
                parameters = definition[1].args.posonlyargs + definition[1].args.args
                if parameters:
                    parameter = parameters[0].arg
                    origin = fresh_incoming_origin(fresh_super[0], parameter)
                    identity = copy.deepcopy(origin['allocation']['receiver_class'])
                    return {parameter: [{'instance_type': identity,
                                         'fresh_receiver_origin': origin}]}
            return seeded_receiver
        ordinary = {argument.arg for argument in definition[1].args.posonlyargs
                    + definition[1].args.args + definition[1].args.kwonlyargs}
        incoming = dict(seeded_receiver)
        for parameter in sorted(ordinary):
            if parameter in seeded_receiver:
                continue
            arguments = [argument for argument in edge.argument_sources
                         if argument.get('parameter') == parameter]
            records = [item for item in edge.parameter_bindings
                       if item.get('parameter') == parameter]
            exact_super_receiver = (len(fresh_super) == 1 and len(arguments) == 1
                and arguments[0].get('argument') == {'receiver': True}
                and arguments[0].get('sources')
                and all(value.get('fresh_receiver_origin') == fresh_super[0].get('origin')
                    and value.get('relation') == 'direct'
                    and value.get('source') == fresh_super[0].get('origin', {}).get('parameter')
                    and not any(value.get(flag) for flag in (
                        'projection', 'output_path', 'attribute_provenance',
                        'import_modified', 'import_incomplete', 'value_incomplete'))
                    for value in arguments[0]['sources']))
            exact_class_receiver = (len(arguments) == 1
                and arguments[0].get('argument') == {'receiver': True}
                and any(fact.get('status') == 'source_bound'
                    and fact.get('target') == asdict(definition[0])
                    and fact.get('implicit_binding', {}).get('parameter') == parameter
                    and fact.get('implicit_binding', {}).get('status') == 'static_bound'
                    for fact in edge.class_method_bindings))
            if (not records and (exact_super_receiver or exact_class_receiver)):
                records = [{'argument': {'receiver': True}, 'parameter': parameter, 'status': 'exact'}]
            if (not arguments or any(argument.get('target_path') for argument in arguments)
                    or len(records) != 1 or records[0]['status'] != 'exact'):
                continue
            sources = [value for argument in arguments for value in argument.get('sources', [])]
            containers = [argument.get('container_binding') for argument in arguments]
            if (not normal_binding and containers and all(item and item == containers[0] for item in containers)
                    and containers[0]['status'] == 'exact'):
                incoming[parameter] = [{'container_shape': containers[0]['shape'],
                    'container_binding': copy.deepcopy(containers[0])}]
                literals = [argument.get('literal') for argument in arguments]
                if literals[0] is not None and all(item == literals[0] for item in literals):
                    incoming[parameter][0]['literal'] = copy.deepcopy(literals[0])
                continue
            values = []
            for value in sources:
                if (value.get('kind') == 'constructor_instance' and value.get('instance_type')
                        and records[0].get('argument') == {'constructor_instance': True}
                        and value.get('relation') == 'direct'
                        and not any(value.get(flag) for flag in (
                            'projection', 'output_path', 'value_incomplete'))
                        and any(fact.get('status') == 'source_bound'
                            and fact.get('phase') == '__init__'
                            and fact.get('target') == asdict(definition[0])
                            and fact.get('receiver_class') == value['instance_type']
                            and fact.get('implicit_binding', {}).get('parameter') == parameter
                            for fact in edge.constructor_bindings)):
                    values.append({'instance_type': copy.deepcopy(value['instance_type']),
                        'conditions': copy.deepcopy(value.get('conditions', []))})
                    continue
                if (value.get('kind') in ('parameter', 'call_result')
                        and value.get('instance_type') and value.get('relation') == 'direct'
                        and not any(value.get(flag) for flag in ('projection', 'output_path',
                            'value_incomplete', 'import_modified', 'import_incomplete',
                            'attribute_provenance'))):
                    values.append({'instance_type': copy.deepcopy(value['instance_type']),
                        'conditions': copy.deepcopy(value.get('conditions', []))})
                    bindings = [fact for fact in edge.instance_method_bindings
                                if fact.get('status') == 'source_bound'
                                and fact.get('target') == asdict(definition[0])
                                and records[0].get('argument') == {'receiver': True}]
                    if len(bindings) == 1:
                        values[-1]['fresh_receiver_origin'] = fresh_incoming_origin(bindings[0], parameter)
                    continue
                if value.get('instance_type') or 'instance_candidates' in value:
                    values.append({'instance_candidates': [], 'value_incomplete': True})
                    continue
                origin = value.get('source_class_origin', {})
                if (origin.get('basis') == 'source_symbol' and value.get('class_type')
                        and origin.get('class') == value['class_type']
                        and value.get('relation') == 'direct' and not any(value.get(flag)
                            for flag in ('projection', 'output_path', 'import_modified',
                                         'import_incomplete', 'value_incomplete', 'attribute_provenance'))):
                    origin = copy.deepcopy(origin)
                    origin['call_context'] = origin.get('call_context', []) + [edge.id]
                    values.append({'class_type': copy.deepcopy(value['class_type']),
                        'source_class_origin': origin,
                        'conditions': copy.deepcopy(value.get('conditions', []))})
                    continue
                identity = value.get('callable_type')
                if value.get('kind') == 'callable':
                    matches = self._definition_index.find(value.get('module'), value['source'])
                    identity = asdict(matches[0][0]) if len(matches) == 1 else None
                if identity and value.get('relation') == 'direct' and not any(
                        value.get(flag) for flag in ('projection', 'output_path',
                            'import_modified', 'import_incomplete', 'value_incomplete')):
                    values.append({'callable_type': identity,
                        'callable_evidence': _unique(value.get('callable_evidence', [])
                            + value.get('evidence', [])),
                        'conditions': value.get('conditions', [])})
            literals = [argument.get('literal') for argument in arguments]
            literal = (literals[0] if all(item == literals[0] for item in literals) else None)
            if normal_binding and literal is not None and literal['type'] in ('tuple', 'list'):
                literal = None
            if literal is not None:
                values = [dict(value, literal=copy.deepcopy(literal)) for value in values] or [
                    {'literal': copy.deepcopy(literal),
                     'literal_evidence': _unique([evidence for argument in arguments
                         for evidence in argument.get('value_evidence', [])])}]
            if values:
                mutations = _unique([effect for value in sources
                    for effect in value.get('class_lookup_mutations', [])])
                if mutations:
                    for value in values:
                        if value.get('class_type') or value.get('instance_type'):
                            value['class_lookup_mutations'] = copy.deepcopy(mutations)
                incomplete = len(values) != len(sources) or any(
                    not argument.get('sources') for argument in arguments)
                if literal is not None:
                    incomplete = False
                incoming[parameter] = [dict(value, value_incomplete=True)
                                       if incomplete else value for value in values]
                if normal_binding:
                    condition = {'normal_call_binding': {
                        'call_id': edge.id, 'parameter': parameter,
                        'argument': copy.deepcopy(records[0]['argument'])}}
                    for value in incoming[parameter]:
                        value['conditions'] = _unique(value.get('conditions', []) + [condition])
        if normal_binding:
            return incoming
        for name in self._captures(*definition):
            records = [item for item in edge.capture_bindings if item.get('capture') == name]
            if len(records) != 1:
                continue
            binding = records[0].get('container_binding', {})
            contents = records[0].get('current_sources', [])
            if (binding.get('status') == 'exact' and not binding.get('contents_unknown')
                    and binding.get('shape') in ('dict', 'list', 'tuple')
                    and any(value.get('kind') in ('parameter', 'capture')
                        and value.get('relation') == 'contained' and value.get('output_path') == ['*']
                        and not value.get('projection') and not value.get('value_incomplete')
                        and value.get('container_role') != 'key' for value in contents)):
                incoming[name] = [{'capture_container_binding': copy.deepcopy(binding)}]
        return incoming

    ## Merge fresh mapping checks only when their lookup proofs agree.
    ## 仅在查找证明一致时合并新建映射检查。
    #
    #  @param previous Previously collected checks.
    #  @param current Checks from another context.
    #  @return Bounded merged alternatives, or an empty list when incompatible.
    @staticmethod
    def _merge_fresh_mapping_checks(previous, current):
        """Keep bounded receiver alternatives only when their lookup proof agrees."""
        if previous == current:
            return copy.deepcopy(previous)
        if (not previous or not current or len(previous) > 8 or len(current) > 8
                or any(not isinstance(item, dict) for item in previous + current)):
            return []
        shared_fields = (
            'kind', 'status', 'function', 'mapping_parameter', 'receiver_parameter',
            'key_variable', 'value_variable', 'lookup_variable', 'attribute_template',
            'iteration_evidence', 'lookup_evidence', 'guard_evidence', 'raise_evidence',
            'invocation_evidence', 'key_conditions', 'attribute_requires_nondunder',
            'runtime_lookup_confirmed', 'runtime_rejection_confirmed', 'receiver_class',
            'member_names', 'source_hash', 'source_hashes', 'assumptions')
        reference = previous[0]
        if any(any(item.get(field) != reference.get(field) for field in shared_fields)
               for item in previous[1:] + current):
            return []
        merged = _unique(copy.deepcopy(previous) + copy.deepcopy(current))
        return merged if len(merged) <= 8 else []

    ## Merge one context summary while retaining unresolved alternatives.
    ## 合并单个上下文摘要，同时保留未解析候选的不确定性。
    #
    #  @param result Mutable combined analysis snapshot.
    #  @param summary Context-specific summary snapshot.
    #  @return None
    def _merge_summary(self, result, summary):
        result.boundaries.extend(summary.boundaries)
        for function in summary.functions:
            previous = next((item for item in result.functions
                             if item['function'] == function['function']), None)
            if previous is None:
                result.functions.append(copy.deepcopy(function))
            else:
                previous['fresh_mapping_member_checks'] = self._merge_fresh_mapping_checks(
                    previous.get('fresh_mapping_member_checks', []),
                    function.get('fresh_mapping_member_checks', []))
                for field in ('returns', 'mapping_effects', 'loops', 'receiver_contexts',
                              'return_objects', 'decorator_effects', 'context_managers',
                              'cached_local_imports', 'source_wrapper_forwarding',
                              'native_callable_metadata_queries', 'native_class_metadata_observers'):
                    if field in function:
                        previous[field] = _unique(previous.get(field, []) + function[field])
        for call in summary.calls:
            previous = next((item for item in result.calls if item.id == call.id), None)
            if previous is None:
                result.calls.append(copy.deepcopy(call))
            else:
                unresolved = any(item.target is None and item.target_status not in (
                    'bounded_alternatives', 'builtin_allocation', 'python_protocol',
                    'local_container_protocol') for item in (previous, call))
                if previous.target != call.target:
                    previous.target = None
                    previous.target_status = 'bounded_alternatives'

                # An unresolved context prevents a unique target and complete value proof.
                # 未解析的上下文会阻止唯一目标和完整值的证明。
                if unresolved:
                    previous.target = None
                    previous.target_status = ('receiver_unresolved'
                        if '.' in previous.callee_name else 'definition_unavailable')
                for field in ('target_candidates', 'argument_sources', 'argument_flows',
                              'parameter_bindings', 'parameter_flows', 'return_flows',
                              'receiver_sources', 'receiver_type_evidence',
                              'binding_issues', 'mutation_flows', 'effects', 'capture_bindings',
                              'return_dependencies', 'decorator_identity_evidence'):
                    setattr(previous, field, _unique(getattr(previous, field) + getattr(call, field)))
                for field in ('callable_sources', 'analysis_contexts', 'conditional_returns',
                              'class_method_bindings', 'constructor_bindings', 'instance_method_bindings', 'class_metadata_bindings',
                              'class_read_bindings', 'conditional_source_bindings', 'candidate_paths'):
                    setattr(previous, field, _unique(getattr(previous, field) + getattr(call, field)))
                if previous.callable_instance_evidence != call.callable_instance_evidence:
                    previous.callable_instance_evidence = {}
                previous.result_sources = _merge_result_sources(
                    previous.result_sources, call.result_sources)
                if unresolved:
                    previous.result_sources = [dict(value, value_incomplete=True)
                        if value.get('class_type') or value.get('instance_type') or value.get('instance_candidates')
                        or value.get('container_object') else value
                        for value in previous.result_sources]
                if previous.binding_status != call.binding_status:
                    previous.binding_status = 'uncertain'

    ## Expand the selected call target, retaining existing function summaries.
    ## 展开选定调用目标，并保留已有函数摘要。
    #
    #  @param result Previous snapshot from this source set.
    #  @param call_id Exact call-site identifier.
    #  @param additional_depth Layers below the selected target.
    #  @param isolate Return only the selected incoming context, without merging the caller snapshot.
    #  @param preserve_lineage Retain available origin call facts in isolated expansion.
    #  @return New snapshot, leaving result unchanged.
    def expand(self, result, call_id, additional_depth=1, isolate=False,
               preserve_lineage=False):
        if type(isolate) is not bool:
            raise ValueError('isolate must be bool')
        if type(preserve_lineage) is not bool:
            raise ValueError('preserve_lineage must be bool')
        if preserve_lineage and not isolate:
            raise ValueError('preserve_lineage requires isolate=True')
        if additional_depth < 1:
            raise ValueError('additional_depth must be positive')
        max_class_effect_steps = result.inputs.get('max_class_effect_steps', 8000)
        if type(max_class_effect_steps) is not int or max_class_effect_steps < 1:
            raise ValueError('Class-effect analysis budget must be a positive integer')
        dependencies = result.inputs.get('supporting_source_sha256', {})
        if dependencies and not self.support_source_protocols:
            raise ValueError('Supporting source protocols are not enabled for expansion')
        validate_source_dependencies(dependencies, self._analysis_budget)
        self._index(preserve_source_facts=True)
        # Expansion is part of the same query snapshot. Keep its class-effect
        # allowance aligned with the budget that produced the parent facts.
        self._class_effect_fact_steps = max_class_effect_steps
        self._conditional_source_state = result.inputs.get('conditional_source_state') is True
        self._supporting_source_hashes.update(dependencies)
        # The parent snapshot and the expansion must use the same sources and contracts.
        # 父快照与本次展开必须使用相同源码和契约。
        if (self.hashes != result.inputs['sha256'] or sorted(self.files) != result.inputs['source_files']
                or self.return_summaries != result.inputs.get('return_summaries', {})
                or self.parameter_shapes != result.inputs.get('parameter_shapes', {})):
            raise ValueError('Sources changed; call analyze again before expand')
        call = next(c for c in result.calls if c.id == call_id)
        if isolate:
            if call.target is None or call.binding_status == 'invalid':
                raise ValueError('Isolated expansion requires a unique usable target')
            definition = next(d for d in self._definition_index.find(call.target.module, call.target.qualname)
                              if d[0] == call.target)
            inputs = copy.deepcopy(result.inputs)
            if not preserve_lineage:
                inputs.pop('entry_binding', None)
                inputs.pop('entry_alias', None)
            inputs['expansion_context'] = {'incoming_call_id': call.id,
                'caller': asdict(call.caller), 'target': asdict(call.target),
                'parameter_facts': copy.deepcopy(self._incoming_facts(definition, call))}
            updated = FlowAnalysis(call.target, inputs)
            if preserve_lineage:
                lineage_ids = {call.id}
                for binding in getattr(call, 'instance_method_bindings', ()):
                    origin = binding.get('origin') if isinstance(binding, dict) else None
                    if isinstance(origin, dict) and isinstance(origin.get('path'), (list, tuple)):
                        lineage_ids.update(item for item in origin['path'] if isinstance(item, str))
                for value in getattr(call, 'receiver_sources', ()):
                    origin = value.get('fresh_receiver_origin') if isinstance(value, dict) else None
                    if isinstance(origin, dict) and isinstance(origin.get('path'), (list, tuple)):
                        lineage_ids.update(item for item in origin['path'] if isinstance(item, str))
                lineage_calls = [item for item in result.calls if item.id in lineage_ids]
                if ({item.id for item in lineage_calls} != lineage_ids
                        or sum(item.id == call.id for item in lineage_calls) != 1):
                    raise ValueError('Expansion lineage call facts are incomplete')
                updated.calls = copy.deepcopy(lineage_calls)
                updated.boundaries = copy.deepcopy([
                    item for item in result.boundaries
                    if item.get('call_id') in lineage_ids
                    or item.get('reason') == 'source_constructor_entry_binding'])
            # The selected edge starts a bounded context. Recursion below this
            # entry is still checked by _walk; no root facts are merged into it.
            # 选定边作为独立有界上下文，后续递归仍由 _walk 检查。
            context = CallContext(call.caller.module, call.target, copy.deepcopy(call))
            self._walk(updated, definition, additional_depth, context, 500, 2000)
            updated.boundaries = _unique(updated.boundaries)
            publish_source_dependencies(self, updated)
            return updated
        updated = copy.deepcopy(result)
        if call.target is not None:
            updated.boundaries = [b for b in updated.boundaries if not (b.get('call_id') == call_id and b['reason'] == 'depth_limit')]
            # Selected expansion retains its original caller-only recursion
            # ancestry; it does not infer an entry path from the merged graph.
            parent = CallContext(call.caller.module, call.caller, None)
            selected = next(c for c in updated.calls if c.id == call_id)
            context = CallContext(call.caller.module, call.target, selected, parent)
            definition = next(d for d in self._definition_index.find(call.target.module, call.target.qualname)
                              if d[0] == call.target)
            self._walk(updated, definition, additional_depth, context, 500, 2000)
        updated.boundaries = _unique(updated.boundaries)
        publish_source_dependencies(self, updated)
        return updated


## Summarize one function under a bounded incoming call context.
## 在有界传入调用上下文下概括单个函数。
