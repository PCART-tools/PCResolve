## @package pcresolve.flow.transfer.summary_effects
#  Apply supported function and mapping effects.
#
#
#  Propagates call effects and widens mapping remainder facts when needed.
#  传播调用效果，并在需要时扩大映射余项事实的保守范围。



import ast
import copy
from dataclasses import asdict
from pcresolve.facts.effect_facts import (FunctionEffect, finite_key_delete_sites,
                                          instance_field_write_sites)
from pcresolve.flow.proofs.containers.mapping_remainders import (
    _ProofLimit,
    mapping_remainder,
)
from pcresolve.flow.proofs.callables._fresh_receiver import _closed_layout
from pcresolve.flow.transfer._summary_support import _call_key, _loop_env, _unique


## Apply supported function and mapping effects inside flow summaries.
## 在流摘要中应用受支持的函数效果和映射效果。
class EffectsMixin:
    ## Prove a narrow fresh plain-object field store on a straight-line prefix.
    ## 证明直线语句前缀中新建普通对象的字段存储。
    #
    #  @param node Current call expression.
    #  @param target_ref Resolved source function.
    #  @param target Source definition for the function.
    #  @param effect Indexed field write.
    #  @param receivers Bound receiver values.
    #  @param env Current abstract environment.
    #  @return True only when the bounded source proof succeeds.
    def plain_fresh_field_store(self, node, target_ref, target, effect, receivers, env):
        if (len(receivers) != 1 or not isinstance(node.func, ast.Name)
                or not isinstance(target, ast.FunctionDef) or target.decorator_list
                or effect.attribute in ('__class__', '__dict__', '__weakref__')
                or len(target.body) != 1 or not isinstance(target.body[0], ast.Assign)
                or len(target.body[0].targets) != 1
                or not isinstance(target.body[0].value, ast.Name)
                or not isinstance(effect.statement, ast.Assign)
                or not isinstance(node.args[0] if node.args else None, ast.Name)):
            return False
        receiver = receivers[0]
        identity = receiver.get('instance_type')
        if (receiver.get('kind') != 'call_result' or not identity
                or receiver.get('value_incomplete') or receiver.get('conditions')
                or receiver.get('projection') or receiver.get('output_path')
                or self.class_origin_invalid(identity, env)):
            return False
        ref = type(target_ref)(**identity)
        matches = self.analyzer._definition_index.find(ref.module, ref.qualname, kind='class')
        if (len(matches) != 1 or matches[0][0] != ref
                or not self.analyzer._ordinary_construction(ref)):
            return False
        cls = matches[0][1]
        if (cls.bases or cls.keywords or cls.decorator_list
                or not all(isinstance(statement, ast.Pass) for statement in cls.body)
                or not self.analyzer._stable_import_name(ref.module + '.' + ref.qualname)
                or not _closed_layout(self.analyzer, [(ref, cls)], effect.attribute)):
            return False
        body = self.node.body
        if not body or not isinstance(body[0], ast.Assign) or len(body[0].targets) != 1:
            return False
        allocation = body[0]
        obj = node.args[0].id
        if (not isinstance(allocation.targets[0], ast.Name)
                or allocation.targets[0].id != obj or not isinstance(allocation.value, ast.Call)
                or not isinstance(allocation.value.func, ast.Name)
                or allocation.value.args or allocation.value.keywords
                or allocation.value.func.id != ref.qualname
                or receiver.get('source') != _call_key(self.ref.file_path, allocation.value)
                or ref.module != self.ref.module):
            return False
        for statement in body[1:]:
            if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
                return False
            invocation = statement.value
            if (not isinstance(invocation.func, ast.Name) or invocation.func.id != node.func.id
                    or invocation.keywords or len(invocation.args) != len(node.args)
                    or not all(isinstance(arg, ast.Name) for arg in invocation.args)
                    or invocation.args[0].id != obj):
                return False
            if invocation is node:
                return True
        return False

    ## Describe unmodeled alternatives where a candidate field write may not apply.
    ## 描述候选字段写入可能未生效且尚未建模的替代路径。
    #
    #  @param target_ref Function containing the candidate write sites.
    #  @param conditions Ordered caller and callee source guards.
    #  @param contexts Syntactic exception or execution contexts around the write.
    #  @param call Call whose target and binding status bound the summary.
    #  @param partial Whether the method summary omitted unsupported behavior.
    #  @param class_method Whether the selected source definition is a class method.
    #  @return Possible guard complements and explicit unresolved alternatives.
    def field_write_alternatives(self, target_ref, conditions, contexts, call, partial,
                                 class_method):
        alternatives = []
        prefix = []
        for condition in conditions:
            if type(condition.get('branch')) is bool and 'test' in condition:
                alternatives.append({
                    'kind': 'guard_not_satisfied',
                    'status': 'possible',
                    'guard_path': copy.deepcopy(prefix) + [dict(
                        condition, branch=not condition['branch'])]})
            prefix.append(condition)
        if call.target_status != 'resolved':
            alternatives.append({'kind': 'target_or_dispatch_unresolved',
                'status': 'unproven', 'target_status': call.target_status})
        if class_method:
            alternatives.append({'kind': 'dynamic_method_dispatch_unproven',
                'status': 'unproven', 'resolved_source_target': True})
        alternatives.append({'kind': 'field_store_unproven', 'status': 'unproven',
                             'detail': 'descriptor_or_custom_setattr'})
        if partial:
            alternatives.append({'kind': 'method_effects_incomplete',
                'status': 'unproven'})
        if contexts:
            alternatives.append({'kind': 'execution_completion_unproven',
                'status': 'unproven', 'contexts': [
                    {'kind': kind, 'evidence': self.evidence_at(target_ref, context)}
                    for kind, context in contexts]})
        return alternatives

    ## Summarize ordered candidate values for each instance field written by a call.
    ## 汇总一次调用中每个实例字段的有序候选写入值。
    #  This is a source-order summary, not a runtime heap postcondition.
    #
    #  @param call Call record containing the extracted field writes.
    #  @param partial Whether the source method has unsupported behavior.
    #  @return None. Appends one bounded candidate-state record per field.
    def append_field_state_candidates(self, call, partial):
        groups = {}
        for effect in call.effects:
            if effect.get('kind') != 'instance_field_write':
                continue
            groups.setdefault(effect.get('field_key'), []).append(effect)
        for field_key, writes in groups.items():
            alternatives = []
            for index, write in enumerate(writes):
                write_contexts = tuple((item.get('kind'),
                    item.get('evidence', {}).get('file_path'),
                    item.get('evidence', {}).get('lineno'))
                    for item in write.get('contexts', []))
                write_conditions = {(
                    item.get('test', {}).get('file_path'),
                    item.get('test', {}).get('lineno'),
                    item.get('test', {}).get('col_offset')): item.get('branch')
                    for item in write.get('conditions', [])}
                later_writes = []
                for later in writes[index + 1:]:
                    later_contexts = tuple((item.get('kind'),
                        item.get('evidence', {}).get('file_path'),
                        item.get('evidence', {}).get('lineno'))
                        for item in later.get('contexts', []))
                    if later_contexts != write_contexts:
                        continue
                    survival_paths = []
                    compatible = True
                    additional_conditions = 0
                    prefix = []
                    for condition in later.get('conditions', []):
                        test = condition.get('test', {})
                        identity = (test.get('file_path'), test.get('lineno'),
                                    test.get('col_offset'))
                        branch = condition.get('branch')
                        if identity in write_conditions:
                            if write_conditions[identity] != branch:
                                compatible = False
                                break
                        elif type(branch) is bool:
                            additional_conditions += 1
                            survival_paths.append(copy.deepcopy(prefix) + [dict(
                                condition, branch=not branch)])
                        prefix.append(condition)
                    if not compatible:
                        continue
                    later_writes.append({
                        'write': copy.deepcopy(later.get('evidence', [{}])[0]),
                        'conditions': copy.deepcopy(later.get('conditions', [])),
                        'survives_when': survival_paths,
                        'unconditional_after': additional_conditions == 0})
                alternatives.append({
                    'write': copy.deepcopy(write.get('evidence', [{}])[0]),
                    'value_expression': copy.deepcopy(write.get('value_expression')),
                    'conditions': copy.deepcopy(write.get('conditions', [])),
                    'contexts': copy.deepcopy(write.get('contexts', [])),
                    'write_order': write.get('write_order'),
                    'later_same_route_writes': later_writes})
            call.effects.append({
                'kind': 'instance_field_state_candidates',
                'field_key': field_key,
                'field': writes[0].get('field'),
                'receiver': copy.deepcopy(writes[0].get('receiver')),
                'status': 'source_candidate',
                'completeness': 'partial' if partial else 'source_summary',
                'completion': 'unproven' if partial or any(
                    write.get('completion') != 'normal_return' for write in writes)
                    else 'normal_return',
                'uncertainty_reasons': sorted({alternative.get('kind')
                    for write in writes
                    for alternative in write.get('non_write_alternatives', [])
                    if alternative.get('status') == 'unproven'}),
                'candidate_values': alternatives,
                'call_id': call.id})

    ## Apply a resolved function's supported effects to the caller environment.
    ## 将已解析函数支持的效果应用到调用方环境。
    #
    #  @param definition Resolved function reference and its source function node.
    #  @param actuals Value facts supplied for each parameter name.
    #  @param captures Value facts bound to lexical captures.
    #  @param call Call record receiving effects and mutation flows.
    #  @param env Caller environment updated for writes and container mutations.
    #  @param node Source call node providing evidence for applied effects.
    #  @return True when every supported effect was applied exactly, otherwise False.
    def apply_effects(self, definition, actuals, captures, call, env, node):
        # Apply complete summaries to proven objects on normal completion.
        # Unsupported mapping effects widen exclusions without inventing writes.
        target_ref, target = definition
        effects, cause = self.analyzer._function_effects(definition)
        partial_field_effects = False
        if effects is None and cause not in (
                'mapping_effect_budget', 'recursive_helper_effects', 'literal_branch_budget'):
            field_sites = instance_field_write_sites(target)
            if field_sites:
                effects = field_sites
                partial_field_effects = True
        mapping_candidate = any(
            isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
            and child.func.attr == 'pop' or
            isinstance(child, ast.Delete) and any(isinstance(item, ast.Subscript)
                                                 for item in child.targets)
            or isinstance(child, ast.Subscript) and isinstance(child.ctx, ast.Store)
            for child in ast.walk(target))
        affected = [value for inputs in actuals.values() for value in inputs]
        affected_roots, affected_unknown = self.mapping_affected_values(affected, env)
        impact = {'affected_values': affected_roots,
                  'affected_scope': 'unknown' if affected_unknown else
                                    'known' if affected_roots else 'none'}
        if partial_field_effects:
            self.add_boundary('instance_field_effect_partial', node, env, affected,
                call_id=call.id, detail=cause, write_sites=len(effects))
        if effects is None:
            if cause != 'mapping_effect_budget' and self.mapping_remainder_effect(
                    definition, actuals, call, env, node):
                return False  # Only unaffected keys are complete, never the whole helper.
            ordinary = {argument.arg for argument in target.args.posonlyargs
                        + target.args.args + target.args.kwonlyargs}
            ordinary_actuals = {name: values for name, values in actuals.items() if name in ordinary}
            known_mapping = any(value.get('kind') == 'container' and value.get('container_shape') == 'dict'
                for values in ordinary_actuals.values() for value in self.container_values(values))
            if known_mapping:
                for values in ordinary_actuals.values():
                    self.unknown_container_contents(values, env)
            owner = target_ref.qualname.rpartition('.')[0]
            if (cause != 'mapping_effect_budget' and call.binding_status == 'complete'
                    and not getattr(target, 'decorator_list', []) and not owner
                    and self.analyzer._stable_import_name(target_ref.module + '.' + target_ref.qualname)
                    and (target_ref.module, target_ref.qualname) not in self.modified_return_callables):
                for site in finite_key_delete_sites(target):
                    receivers = self.container_values(actuals.get(site.target, []))
                    arguments = [item for item in call.argument_sources if item.get('parameter') == site.source]
                    literal = arguments[0].get('literal') if len(arguments) == 1 else None
                    if (not receivers or not all(value.get('kind') == 'container'
                            and value.get('container_shape') == 'dict'
                            and value.get('relation') == 'direct' and not value.get('value_incomplete')
                            and not value.get('projection') and not value.get('output_path')
                            for value in receivers) or len({value['source'] for value in receivers}) != 1
                            or literal is None or literal['type'] not in ('tuple', 'list')
                            or not all(isinstance(key, str) for key in literal['value'])):
                        continue
                    keys = _unique(literal['value'])
                    if len(keys) > self.analyzer._effect_fact_steps:
                        self.add_boundary('mapping_effect_budget', node, env, affected, call_id=call.id, **impact)
                        break
                    self.analyzer._effect_fact_steps -= len(keys)
                    roots, _ = self.mapping_affected_values(receivers, env)
                    for key in keys:
                        call.effects.append({'kind': 'mapping_element', 'operation': 'delete',
                            'mapping': roots, 'element_path': [key], 'state_after': 'unknown',
                            'status': 'partial_behavior', 'completion': 'unproven',
                            'reachability': 'not_proven', 'conditions': copy.deepcopy(self.conditions),
                            'sequence_binding': {'parameter': site.source,
                                'argument': arguments[0]['argument'], 'literal': literal,
                                'evidence': arguments[0].get('value_evidence', [])},
                            'operation_conditions': [{'test': self.evidence_at(target_ref, site.membership_test),
                                'branch': True, 'iteration_key': key}],
                            'evidence': [self.evidence_at(target_ref, site.statement)],
                            'loop_evidence': self.evidence_at(target_ref, site.sequence_loop),
                            'call_evidence': self.evidence(node), 'call_id': call.id})
            for values in actuals.values():
                self.invalidate_literals(values, env)
            if mapping_candidate or known_mapping:
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                                  call_id=call.id, detail=cause, **impact)
                self.widen_mapping_exclusions(ordinary_actuals, env)
                if cause == 'mapping_effect_budget':
                    self.add_boundary(cause, node, env, affected, call_id=call.id, **impact)
            return False
        expanded, changed_sequences = [], set()
        for effect in effects:
            if effect.kind != 'mapping_delete_keys':
                expanded.append(effect)
                if effect.kind != 'nonlocal_write':
                    changed_sequences.update(value['source'] for value in self.container_values(
                        actuals.get(effect.target, captures.get(effect.target, [])))
                        if value.get('kind') == 'container')
                continue
            sequence_objects = {value['source'] for value in self.container_values(
                actuals.get(effect.source, [])) if value.get('kind') == 'container'}
            if sequence_objects & changed_sequences:
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                    call_id=call.id, detail='modified_finite_sequence', **impact)
                for values in actuals.values():
                    self.invalidate_literals(values, env)
                self.widen_mapping_exclusions(actuals, env)
                return False
            arguments = [argument for argument in call.argument_sources
                         if argument.get('parameter') == effect.source]
            literal = arguments[0].get('literal') if len(arguments) == 1 else None
            if (call.binding_status != 'complete' or literal is None
                    or literal['type'] not in ('tuple', 'list')
                    or not all(isinstance(key, str) for key in literal['value'])):
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                    call_id=call.id, detail='unproven_finite_string_sequence', **impact)
                self.widen_mapping_exclusions(actuals, env)
                return False
            keys = _unique(literal['value'])
            if len(keys) > self.analyzer._effect_fact_steps:
                self.add_boundary('mapping_effect_budget', node, env, affected, call_id=call.id, **impact)
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                    call_id=call.id, detail='mapping_effect_budget', **impact)
                self.widen_mapping_exclusions(actuals, env)
                return False
            self.analyzer._effect_fact_steps -= len(keys)
            expanded.extend(FunctionEffect('mapping_delete', effect.target, effect.source,
                effect.statement, 'dict', (key,), None, effect.sequence_loop, effect.membership_test)
                for key in keys)
        effects = tuple(expanded)
        values_by_name = dict(captures)
        values_by_name.update({name: self.container_values(values)
                               for name, values in actuals.items()})
        all_values_by_name = dict(captures)
        all_values_by_name.update(actuals)
        if effects:
            owner = target_ref.qualname.rpartition('.')[0]
            field_only = all(effect.kind == 'instance_field_write' for effect in effects)
            class_method = bool(owner and self.analyzer._definition_index.find(
                target_ref.module, owner, kind='class'))
            if (call.binding_status != 'complete' or target.decorator_list
                    or class_method and not field_only
                    or (not owner and not self.analyzer._stable_import_name(
                        target_ref.module + '.' + target_ref.qualname))
                    or (target_ref.module, target_ref.qualname) in self.modified_return_callables):
                self.add_boundary('mapping_effect_unproven' if mapping_candidate else
                                  'container_effect_unknown', node, env, affected,
                                  call_id=call.id, detail='unstable_callable_or_binding', **impact)
                self.widen_mapping_exclusions(actuals, env)
                return False
            ordinary = {argument.arg for argument in
                        target.args.posonlyargs + target.args.args + target.args.kwonlyargs}
            if any(effect.kind != 'nonlocal_write' and effect.target not in ordinary
                   for effect in effects):
                self.add_boundary('container_effect_unknown', node, env, affected,
                                  call_id=call.id, detail='non_ordinary_receiver', **impact)
                return False
        mapping_effects = [effect for effect in effects if effect.receiver_shape == 'dict']
        if mapping_effects:
            cause = None
            for effect in effects:
                receivers = values_by_name.get(effect.target, [])
                shapes = ('dict',) if effect.receiver_shape else (
                    ('list',) if effect.kind == 'container_append' else ('dict', 'list', 'set'))
                if (effect.kind == 'nonlocal_write' or not receivers or not all(
                        value.get('kind') == 'container'
                        and value.get('container_shape') in shapes
                        and value.get('relation') == 'direct'
                        and not value.get('value_incomplete')
                        and not value.get('projection') and not value.get('output_path')
                        and value['source'] in env for value in receivers)
                        or len({value['source'] for value in receivers}) != 1):
                    cause = 'unproven_dict_object'
                    break
            if cause:
                self.add_boundary('mapping_effect_unproven', node, env, affected,
                                  call_id=call.id, detail=cause, **impact)
                self.widen_mapping_exclusions(actuals, env)
                return False
        complete = not partial_field_effects
        field_write_history = {}
        for effect in effects:
            kind = effect.kind
            target_name = effect.target
            source_name = effect.source
            if kind == 'nonlocal_write':
                values = values_by_name.get(source_name, [])
                env[target_name] = self.marked(values, node)
                call.effects.append({'kind': 'nonlocal_write', 'target': target_name,
                                     'source': source_name, 'status': 'exact',
                                     'evidence': [self.evidence_at(
                                         target_ref, effect.statement)]})
                call.mutation_flows.extend(dict(value, target_binding=target_name,
                                                effect_summary='nonlocal_write')
                                           for value in self.materialize(values, env))
                continue
            if kind == 'instance_field_write':
                receivers = all_values_by_name.get(target_name, [])
                receiver_parameters = target.args.posonlyargs + target.args.args
                if (not receivers and receiver_parameters
                        and receiver_parameters[0].arg == target_name):
                    receivers = call.receiver_sources
                field_keys = self.instance_field_keys(receivers, effect.attribute)
                if len(field_keys) != 1:
                    complete = False
                    self.add_boundary('instance_field_effect_unproven', node, env, receivers,
                        call_id=call.id, detail='receiver_identity_unproven',
                        field=effect.attribute)
                    continue
                source_expression = effect.source_expression
                if isinstance(source_name, str):
                    source_values = all_values_by_name.get(source_name, [])
                elif isinstance(source_expression, ast.Name):
                    source_values = all_values_by_name.get(source_expression.id, [])
                elif isinstance(source_expression, (ast.Constant, ast.Tuple, ast.List)):
                    try:
                        literal_value = ast.literal_eval(source_expression)
                        literal_valid = True
                    except (ValueError, TypeError, SyntaxError):
                        literal_value = None
                        literal_valid = False
                    if not literal_valid:
                        source_values = []
                    else:
                        source_values = [{'kind': 'literal',
                            'source': repr(literal_value),
                            'literal': self.literal_fact(source_expression, env),
                            'relation': 'direct',
                            'evidence': [self.evidence_at(target_ref, source_expression)],
                            'conditions': []}]
                else:
                    source_values = []
                    receiver_names = {argument.arg for argument in receiver_parameters[:1]}
                    if isinstance(source_expression, ast.AST):
                        for expression in ast.walk(source_expression):
                            if (isinstance(expression, ast.Attribute)
                                    and isinstance(expression.value, ast.Name)
                                    and expression.value.id in receiver_names):
                                keys = self.instance_field_keys(receivers, expression.attr)
                                for source_key in keys:
                                    existing = env.get(source_key, [])
                                    if not existing:
                                        existing = [{'kind': 'instance_field',
                                            'source': source_key, 'field': expression.attr,
                                            'receiver': copy.deepcopy(receivers[0]),
                                            'relation': 'direct',
                                            'evidence': [self.evidence_at(
                                                target_ref, expression)],
                                            'conditions': []}]
                                    source_values.extend(existing)
                    for expression in ast.walk(source_expression) if isinstance(
                            source_expression, ast.AST) else ():
                        if (isinstance(expression, ast.Name)
                                and expression.id in all_values_by_name
                                and expression.id not in receiver_names):
                            source_values.extend(all_values_by_name[expression.id])
                    if not source_values:
                        source_values = [{'kind': 'derived_expression',
                            'source': ast.unparse(source_expression),
                            'relation': 'derived',
                            'evidence': [self.evidence_at(target_ref, source_expression)],
                            'conditions': []}]
                if not source_values:
                    complete = False
                    self.add_boundary('instance_field_effect_unproven', node, env, receivers,
                        call_id=call.id, detail='write_value_unresolved',
                        field=effect.attribute)
                    continue
                field_key = field_keys[0]
                previous = env.get(field_key, [])
                if not previous:
                    previous = [{'kind': 'instance_field', 'source': field_key,
                        'field': effect.attribute, 'receiver': copy.deepcopy(receivers[0]),
                        'relation': 'direct', 'evidence': [self.evidence(node)],
                        'conditions': []}]
                effect_conditions = [
                    {'test': self.evidence_at(target_ref, test), 'branch': branch}
                    for test, branch in effect.conditions]
                conditions = _unique(copy.deepcopy(self.conditions) + effect_conditions)
                history = field_write_history.get(field_key, [])
                exact_write = (not partial_field_effects and not class_method
                    and not effect.contexts and not effect.conditions
                    and call.target_status == 'resolved' and call.binding_status == 'complete'
                    and self.plain_fresh_field_store(
                        node, target_ref, target, effect, receivers, env))
                non_write_alternatives = self.field_write_alternatives(
                    target_ref, conditions, effect.contexts, call, partial_field_effects,
                    class_method)
                if exact_write:
                    non_write_alternatives = [item for item in non_write_alternatives
                                              if item['kind'] != 'field_store_unproven']
                write_provenance = {
                    'receiver': copy.deepcopy(receivers[0]),
                    'field': effect.attribute,
                    'write': self.evidence_at(target_ref, effect.statement),
                    'call': self.evidence(node),
                    'status': 'exact' if exact_write else 'source_candidate',
                    'write_order': len(history) + 1,
                    'may_overwrite': copy.deepcopy(history),
                    'conditions': copy.deepcopy(conditions),
                    'contexts': [{'kind': kind,
                        'evidence': self.evidence_at(target_ref, context)}
                        for kind, context in effect.contexts],
                    'value_expression': self.evidence_at(target_ref, source_expression)
                        if isinstance(source_expression, ast.AST) else None}
                if exact_write:
                    write_provenance['store_proof'] = {
                        'kind': 'fresh_plain_receiver_straight_line',
                        'receiver_class': copy.deepcopy(receivers[0]['instance_type']),
                        'allocation': self.evidence(self.node.body[0]),
                        'assumptions': ['source_snapshot_bindings_hold',
                                        'no_external_monkeypatch_or_import_hook']}
                tuple_argument = (source_expression.args[0]
                    if isinstance(source_expression, ast.Call) and source_expression.args else None)
                tuple_from_field = (isinstance(tuple_argument, ast.AST)
                    and any(isinstance(item, ast.Attribute)
                        and isinstance(item.value, ast.Name)
                        and item.value.id in {argument.arg for argument in receiver_parameters[:1]}
                        for item in ast.walk(tuple_argument)))
                source_is_tuple = (isinstance(source_expression, ast.Call)
                    and isinstance(source_expression.func, ast.Name)
                    and source_expression.func.id == 'tuple'
                    and len(source_expression.args) == 1 and not source_expression.keywords
                    and tuple_from_field)
                if source_is_tuple:
                    container_key = '$instance-field-value:%s:%s' % (
                        call.id, self.evidence_at(target_ref, effect.statement)['lineno'])
                    env[container_key] = _unique([dict(value, relation='contained',
                        output_path=['*'], evidence=_unique(copy.deepcopy(
                            value.get('evidence', [])) + [self.evidence_at(
                                target_ref, source_expression)]),
                        instance_field_provenance=dict(copy.deepcopy(write_provenance),
                            prior=copy.deepcopy(value.get('instance_field_provenance'))))
                        for value in source_values])
                    source_values = [{'kind': 'container', 'source': container_key,
                        'container_shape': 'tuple', 'relation': 'derived',
                        'evidence': [self.evidence_at(target_ref, source_expression)],
                        'conditions': []}]
                written = [dict(value, relation='direct' if isinstance(
                    source_expression, (ast.Name, ast.Constant, ast.Tuple, ast.List))
                    else 'derived',
                    evidence=_unique(copy.deepcopy(value.get('evidence', [])) +
                                     [self.evidence(node), self.evidence_at(
                                         target_ref, effect.statement)]),
                    conditions=_unique(copy.deepcopy(value.get('conditions', [])) + conditions),
                    instance_field_provenance=dict(copy.deepcopy(write_provenance),
                        prior=copy.deepcopy(value.get('instance_field_provenance'))))
                    for value in source_values]
                env[field_key] = (_unique(written) if exact_write else
                                  _unique(copy.deepcopy(previous) + written))
                effect_record = {'kind': 'instance_field_write',
                    'receiver': copy.deepcopy(receivers[0]), 'field': effect.attribute,
                    'field_key': field_key, 'source': source_name if isinstance(source_name, str)
                        else ast.unparse(source_expression)
                        if isinstance(source_expression, ast.AST) else None,
                    'status': 'exact' if exact_write else 'source_candidate',
                    'completion': 'normal_return' if exact_write else 'unproven',
                    'conditions': conditions,
                    'preserved_value': {'kind': 'instance_field', 'source': field_key,
                        'field': effect.attribute,
                        'receiver': copy.deepcopy(receivers[0])},
                    'non_write_alternatives': non_write_alternatives,
                    'contexts': [{'kind': kind,
                        'evidence': self.evidence_at(target_ref, context)}
                        for kind, context in effect.contexts],
                    'value_expression': self.evidence_at(target_ref, source_expression)
                        if isinstance(source_expression, ast.AST) else None,
                    'evidence': [self.evidence_at(target_ref, effect.statement)],
                    'call_evidence': self.evidence(node), 'call_id': call.id}
                history = field_write_history.setdefault(field_key, [])
                effect_record['write_order'] = len(history) + 1
                if exact_write:
                    effect_record['store_proof'] = copy.deepcopy(write_provenance['store_proof'])
                effect_record['may_overwrite'] = copy.deepcopy(history)
                history.append(effect_record['evidence'][0])
                call.effects.append(effect_record)
                call.mutation_flows.extend(dict(value, target_field=effect.attribute,
                    target_field_key=field_key,
                    target_receiver=copy.deepcopy(receivers[0]),
                    effect_summary='instance_field_write')
                    for value in self.materialize(written, env))
                continue
            receivers = values_by_name.get(target_name, [])
            self.invalidate_literals(receivers, env)
            expected_shape = 'list' if kind == 'container_append' else None
            if (not receivers or not all(value.get('kind') == 'container'
                    and (expected_shape is None or value.get('container_shape') == expected_shape)
                    for value in receivers)
                    or len({value['source'] for value in receivers}) != 1):
                complete = False
                continue
            if kind in ('mapping_pop', 'mapping_delete'):
                key = effect.element_path[0]
                if isinstance(effect.statement, ast.Return):
                    call.result_sources = self.marked(self.materialize(
                        self.project(receivers, key, env), env), node)
                    for value in call.result_sources:
                        value['evidence'] = _unique(value['evidence'] + [
                            self.evidence_at(target_ref, effect.statement)])
                roots, unknown = self.mapping_affected_values(receivers, env)
                binding = next(item for item in call.parameter_bindings
                               if item.get('parameter') == target_name
                               and item.get('status') == 'exact')
                mapping_effect = {
                    'operation': 'pop' if kind == 'mapping_pop' else 'delete',
                    'mapping': roots, 'element_path': [key],
                    'state_after': 'conditional' if self.conditions else 'absent',
                    'status': 'unknown' if unknown else 'bounded',
                    'completion': 'normal_return', 'may_raise': effect.may_raise,
                    'conditions': _unique(copy.deepcopy(self.conditions) +
                        copy.deepcopy(getattr(target, '_flow_conditions', []))),
                    'call_id': call.id,
                    'binding': copy.deepcopy(binding),
                    'evidence': [self.evidence_at(target_ref, effect.statement)],
                    'call_evidence': self.evidence(node)}
                if effect.sequence_loop is not None:
                    argument = next(item for item in call.argument_sources
                                    if item.get('parameter') == source_name)
                    mapping_effect.update(
                        sequence_binding={'parameter': source_name,
                            'argument': argument['argument'],
                            'literal': copy.deepcopy(argument['literal']),
                            'evidence': copy.deepcopy(argument.get('value_evidence', []))},
                        loop_evidence=self.evidence_at(target_ref, effect.sequence_loop),
                        operation_conditions=[{'test': self.evidence_at(target_ref, effect.membership_test),
                            'branch': True, 'iteration_key': key}])
                self.mapping_effects.append(mapping_effect)
                call.effects.append(dict(mapping_effect, kind='mapping_element'))
                if effect.may_raise:
                    self.add_boundary('mapping_effect_exception_path', node, env, receivers,
                                      call_id=call.id, exception=effect.may_raise,
                                      completion='normal_return',
                                      effect_evidence=mapping_effect['evidence'],
                                      affected_values=roots,
                                      affected_scope='unknown' if unknown else
                                                     'known' if roots else 'none')
                for reference in receivers:
                    remaining = []
                    for value in env.get(reference['source'], []):
                        path = value.get('output_path', [None])
                        if path[0] == key:
                            continue
                        if path[0] == '*':
                            value = dict(value, excluded_paths=_unique(
                                value.get('excluded_paths', []) + [[key]]),
                                evidence=value.get('evidence', []) + mapping_effect['evidence'],
                                conditions=value.get('conditions', []) + list(self.conditions))
                        remaining.append(value)
                    env[reference['source']] = remaining
                    markers = []
                    for marker in env.get(reference['source'] + '$keys', []):
                        if marker['key'] == key:
                            continue
                        if marker['key'] == '*':
                            marker = dict(marker, excluded_keys=_unique(
                                marker.get('excluded_keys', []) + [key]))
                        markers.append(marker)
                    env[reference['source'] + '$keys'] = markers
                continue
            if kind == 'container_clear':
                for reference in receivers:
                    env[reference['source']] = []
                    env[reference['source'] + '$keys'] = []
                    env.pop(reference['source'] + '$state', None)
                call.effects.append({'kind': 'container_clear', 'target': target_name,
                                     'status': 'exact',
                                     'evidence': [self.evidence_at(
                                         target_ref, effect.statement)]})
                continue
            values = values_by_name.get(source_name, [])
            for reference in receivers:
                inserted = [dict(value, output_path=['*'] + value.get('output_path', []))
                            for value in self.marked(values, node)]
                env[reference['source']] = _loop_env({
                    'items': env.get(reference['source'], []) + inserted})['items']
                env[reference['source'] + '$keys'] = [
                    {'kind': 'key', 'source': '*', 'key': '*'}]
                call.mutation_flows.extend(dict(value, target_container=reference['source'],
                    effect_summary='unconditional_append')
                    for value in self.materialize(inserted, env))
            call.effects.append({'kind': 'container_append', 'target': target_name,
                                 'source': source_name, 'status': 'exact',
                                 'evidence': [self.evidence_at(
                                     target_ref, effect.statement)]})
        self.append_field_state_candidates(call, partial_field_effects)
        return complete

    ## Prove and apply the unaffected-key remainder of a mapping helper call.
    ## 证明并应用映射辅助调用中未受影响键的余项。
    #
    #  @param definition Resolved function reference and its source function node.
    #  @param actuals Value facts supplied for each parameter name.
    #  @param call Call record receiving the remainder effect.
    #  @param env Environment holding the proven mapping object.
    #  @param node Source call node providing call and boundary evidence.
    #  @return True when the remainder proof was applied, otherwise False.
    def mapping_remainder_effect(self, definition, actuals, call, env, node):
        ref, target = definition
        if (call.binding_status != 'complete' or call.target_status != 'resolved'
                or getattr(target, '_flow_branch_budget', None) is not None
                or call.binding_issues or ref.qualname.count('.') or target.decorator_list
                or self.analyzer._captures(*definition)
                or not self.analyzer._stable_import_name(ref.module + '.' + ref.qualname)
                or (ref.module, ref.qualname) in self.modified_return_callables
                or any(isinstance(n, (ast.Global, ast.Nonlocal)) for n in ast.walk(self.node))):
            return False
        ordinary = {a.arg for a in target.args.posonlyargs + target.args.args + target.args.kwonlyargs}
        mappings = [(name, self.exact_container(values, ('dict',), env))
                    for name, values in actuals.items() if name in ordinary]
        mappings = [(name, obj) for name, obj in mappings if obj is not None]
        if len(mappings) != 1:
            return False
        parameter, obj = mappings[0]
        source = obj['source']
        if (not source.startswith(('$parameter:', '$heap:', '$copy:'))
                or any(not marker.get('remainder_preserved')
                       for marker in env.get(source + '$state', []))
                or any(value.get('source') == source for name, values in actuals.items()
                       if name != parameter for value in self.container_values(values))):
            return False
        # References stored in another object, capture or external binding can
        # let an unrelated call mutate this object. Such escapes stay unproved.
        # 保存到其他对象、捕获或外部绑定中的引用可能允许无关调用修改对象。
        for name, values in env.items():
            if name.startswith('$') and any(
                    value.get('kind') == 'container' and value.get('source') == source
                    for value in self.container_values(values, allow_contained=True)):
                return False
        aliases = {name for name, values in env.items() if not name.startswith('$') and any(
            value.get('kind') == 'container' and value.get('source') == source
            for value in self.container_values(values))}
        if any(n is not self.node and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
               and any(isinstance(child, ast.Name) and child.id in aliases
                       for child in ast.walk(n)) for n in ast.walk(self.node)):
            return False
        # Lexical stores outside local names are not a fresh-object proof.
        for statement in ast.walk(self.node):
            if isinstance(statement, (ast.Assign, ast.AnnAssign)):
                targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
                if (statement.value is not None and statement.lineno < node.lineno and any(
                        isinstance(n, (ast.Attribute, ast.Subscript))
                        for t in targets for n in ast.walk(t)) and any(
                        isinstance(n, ast.Name) and n.id in aliases
                        for n in ast.walk(statement.value))):
                    return False
        sequences = {}
        for argument in call.argument_sources:
            literal = argument.get('literal')
            if (literal and literal['type'] in ('list', 'tuple')
                    and all(isinstance(key, str) for key in literal['value'])):
                sequences[argument['parameter']] = frozenset(literal['value'])
        sequence_sources = {}
        for name, values in actuals.items():
            literals = [value.get('literal', {}) for value in values]
            if values and all(literal.get('type') in ('list', 'tuple')
                    and all(isinstance(key, str) for key in literal['value'])
                    and value.get('kind') == 'container' and value.get('relation') == 'direct'
                    and not any(value.get(flag) for flag in ('value_incomplete', 'projection',
                                                            'output_path'))
                    for value, literal in zip(values, literals)):
                keys = frozenset(key for literal in literals for key in literal['value'])
                if len(keys) <= 64:
                    sequences[name] = keys
                    sequence_sources[name] = copy.deepcopy(values)
        count = sum(1 for _ in ast.walk(target))
        if count > 2000 or count > self.analyzer._effect_fact_steps:
            self.add_boundary('mapping_remainder_budget', node, env,
                              actuals[parameter], call_id=call.id)
            return False
        self.analyzer._effect_fact_steps -= count
        try:
            proof = mapping_remainder(target, parameter, sequences,
                lambda name: self.analyzer._builtin_name_status(
                    ref, target, name) == 'confirmed_builtin')
        except _ProofLimit:
            self.add_boundary('mapping_remainder_budget', node, env,
                              actuals[parameter], call_id=call.id)
            return False
        if proof is None:
            return False
        paths = [[key] for key in proof.excluded_keys]
        evidence = _unique([self.evidence_at(ref, statement) for statement in proof.evidence])
        contents = []
        for value in env[source]:
            path = value.get('output_path', [])
            if path and path[0] in proof.excluded_keys:
                continue
            if path[:1] == ['*']:
                value = dict(value, excluded_paths=_unique(value.get('excluded_paths', []) + paths),
                             evidence=_unique(value.get('evidence', []) + evidence))
            contents.append(value)
        # Values at touched keys are unknown, not absent. This marker prevents
        # another consumer from treating the subset as a complete finite dict.
        if paths:
            env[source + '$state'] = [{'contents_unknown': True, 'remainder_preserved': True,
                'affected_paths': _unique(paths + [path for state in env.get(source + '$state', [])
                                                 for path in state.get('affected_paths', [])])}]
        env[source] = contents
        binding = next(b for b in call.parameter_bindings if b.get('parameter') == parameter)
        roots, _ = self.mapping_affected_values(actuals[parameter], env)
        obj_fact = {'source': source, 'container_shape': 'dict', 'identity': 'argument_alias',
            'value_completeness': 'unaffected_keys_only',
            'parameter': parameter, 'parameter_container': obj.get('parameter_container'),
            'function': asdict(ref), 'conditions': copy.deepcopy(self.conditions), 'evidence': evidence}
        effect = {'kind': 'mapping_remainder', 'operation': 'preserve_unaffected_keys',
            'call_id': call.id, 'function': asdict(ref), 'mapping': roots,
            'object_source': source, 'parameter': parameter, 'binding': copy.deepcopy(binding),
            'excluded_paths': paths, 'return_path': (list(proof.return_path)
                if proof.return_path is not None else None),
            'completion': 'normal_return', 'status': 'bounded',
            'value_completeness': 'unaffected_keys_only',
            'conditions': copy.deepcopy(self.conditions), 'evidence': evidence,
            'finite_sequence_sources': sequence_sources,
            'call_evidence': self.evidence(node), 'return_object': obj_fact,
            'assumptions': ['fresh_unescaped_builtin_dict', 'source_snapshot_bindings_hold',
                            'no_external_monkeypatch_or_import_hook', 'no_reflective_frame_access']}
        call.effects.append(effect)
        self.add_boundary('mapping_values_partial', node, env, actuals[parameter],
                          call_id=call.id, affected_paths=paths,
                          value_completeness='unaffected_keys_only')
        if proof.return_path:
            heap = '$remainder_tuple:' + call.id
            env[heap] = [dict(self.container_endpoint(call, node, obj_fact),
                              output_path=list(proof.return_path))]
            env[heap + '$keys'] = [{'kind': 'key', 'source': str(i), 'key': i}
                                  for i in range(proof.return_size)]
            call.result_sources = [{'kind': 'container', 'source': heap, 'container_shape': 'tuple',
                'relation': 'direct', 'evidence': [self.evidence(node)],
                'conditions': copy.deepcopy(self.conditions)}]
        return True

    ## Add owning parameter roots to the roots affected by the given values.
    ## 为给定值影响到的根补充其所属的参数根。
    #
    #  @param values Value facts whose affected roots are collected.
    #  @param env Environment used to resolve the value facts.
    #  @return Affected roots with owner parameters, and an unknown flag.
    def mapping_affected_values(self, values, env):
        roots, unknown = self.affected_values(values, env)
        for reference in self.container_values(values):
            name = reference.get('parameter_container')
            if (reference.get('kind') == 'container' and name
                    and not any(root['kind'] == 'parameter' and root['name'] == name
                                for root in roots)):
                roots.append({'kind': 'parameter', 'name': name, 'element_path': []})
        return roots, unknown

    ## Widen dict exclusions so unproven mutations stay conservative.
    ## 扩大字典排除范围，使未证明的修改保持保守。
    #
    #  @param actuals Value facts supplied for each parameter name.
    #  @param env Environment holding the affected mapping containers.
    #  @return None
    def widen_mapping_exclusions(self, actuals, env):
        for inputs in actuals.values():
            for reference in self.container_values(inputs):
                if reference.get('kind') != 'container' or reference.get('container_shape') != 'dict':
                    continue
                source = reference['source']
                env[source] = [dict(value, excluded_paths=[])
                               if value.get('excluded_paths') else value
                               for value in env.get(source, [])]
                env[source + '$keys'] = _unique([
                    dict(marker, excluded_keys=[]) if marker.get('excluded_keys') else marker
                    for marker in env.get(source + '$keys', [])] +
                    [{'kind': 'key', 'source': '*', 'key': '*'}])
