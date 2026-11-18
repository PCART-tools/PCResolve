## @package pcresolve.flow.transfer.summary_effects
#  Apply supported function and mapping effects.
#
#
#  Propagates call effects and widens mapping remainder facts when needed.
#  传播调用效果，并在需要时扩大映射余项事实的保守范围。



import ast
import copy
from dataclasses import asdict
from pcresolve.facts.effect_facts import FunctionEffect, finite_key_delete_sites
from pcresolve.flow.proofs.containers.mapping_remainders import (
    _ProofLimit,
    mapping_remainder,
)
from pcresolve.flow.transfer._summary_support import _loop_env, _unique


class EffectsMixin:
    def apply_effects(self, definition, actuals, captures, call, env, node):
        # Apply complete summaries to proven objects on normal completion.
        # Unsupported mapping effects widen exclusions without inventing writes.
        target_ref, target = definition
        effects, cause = self.analyzer._function_effects(definition)
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
        if effects:
            owner = target_ref.qualname.rpartition('.')[0]
            if (call.binding_status != 'complete' or target.decorator_list
                    or self.analyzer._definition_index.find(target_ref.module, owner, kind='class')
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
        complete = True
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
        return complete

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

    def mapping_affected_values(self, values, env):
        roots, unknown = self.affected_values(values, env)
        for reference in self.container_values(values):
            name = reference.get('parameter_container')
            if (reference.get('kind') == 'container' and name
                    and not any(root['kind'] == 'parameter' and root['name'] == name
                                for root in roots)):
                roots.append({'kind': 'parameter', 'name': name, 'element_path': []})
        return roots, unknown

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
