## @package pcresolve.flow.transfer.summary_containers
## @brief Containers operations for query-local flow summaries.

import ast
import copy
from dataclasses import asdict
from pcresolve.facts.effect_facts import container_method_effect
from pcresolve.facts.return_resolution import select_dependencies
from pcresolve.flow.transfer._summary_support import _loop_env, _unique


class ContainersMixin:
    def container_values(self, values, allow_contained=False):
        converted = []
        for value in values:
            obj = value.get('container_object')
            if (obj and value.get('relation') == 'direct'
                    and not value.get('projection')
                    and (allow_contained or not value.get('output_path'))
                    and not value.get('value_incomplete')):
                converted.append(dict(value, kind='container', source=obj['source'],
                    container_shape=obj['container_shape'],
                    parameter_container=obj.get('parameter_container')))
            else:
                converted.append(value)
        return converted

    def incoming_copy_receiver(self, node, values, call, env):
        if node.args or node.keywords or not values or not all(
                value.get('kind') == 'parameter' and value.get('relation') == 'direct'
                and not any(value.get(flag) for flag in ('projection', 'output_path', 'value_incomplete'))
                for value in values):
            return None
        bindings = [self.incoming.get(value['source'], []) for value in values]
        if not all(len(items) == 1 and items[0].get('container_shape') == 'dict'
                and items[0].get('container_binding', {}).get('status') == 'exact'
                and not items[0]['container_binding'].get('contents_unknown') for items in bindings):
            return None
        origins = {items[0]['container_binding']['source'] for items in bindings}
        aliases = {name for name, facts in self.incoming.items() if any(
            fact.get('container_binding', {}).get('source') in origins for fact in facts)}
        if any(value.get('source') in aliases for previous in self.calls
                for value in previous.receiver_sources + [value for argument in previous.argument_sources
                    for value in argument.get('sources', [])]):
            return None
        if any(boundary.get('affected_scope') == 'unknown' or any(
                value.get('name', value.get('source')) in aliases
                for value in boundary.get('affected_values', [])) for boundary in self.result.boundaries
                if boundary.get('function') == asdict(self.ref)):
            return None
        heap = '$incoming_copy:' + call.id
        env[heap] = [dict(value, relation='contained', output_path=['*']) for value in values]
        env[heap + '$keys'] = [{'kind': 'key', 'source': '*', 'key': '*'}]
        return [{'kind': 'container', 'source': heap, 'container_shape': 'dict',
                 'relation': 'direct', 'evidence': [self.evidence(node.func.value)], 'conditions': []}]

    def returned_container(self, target, call, actuals, env, node, effects_complete=False):
        references = [value for values in actuals.values()
                      for value in self.container_values(values)
                      if value.get('kind') == 'container']
        if target is None or not references:
            return None
        remainder = next((effect for effect in call.effects
                          if effect.get('kind') == 'mapping_remainder'
                          and effect.get('return_path') == []), None)
        if remainder is not None:
            return copy.deepcopy(remainder['return_object'])
        fact, cause = self.analyzer._object_returns(target)
        if (target[0].module, target[0].qualname) in self.modified_return_callables:
            fact, cause = None, 'modified_return_callable'
        values = self.container_values(actuals.get(fact['parameter'], [])) if fact else []
        if fact and call.binding_status != 'complete':
            cause = 'uncertain_object_binding'
        elif fact and fact.get('effects') and not effects_complete:
            cause = 'unmodeled_helper_effects'
        elif fact and not (values and all(
                value.get('kind') == 'container' and value.get('relation') == 'direct'
                and not value.get('value_incomplete') and not value.get('projection')
                and not value.get('output_path') and value['source'] in env
                and value.get('container_shape') in ('dict', 'list', 'tuple')
                for value in values) and len({value['source'] for value in values}) == 1):
            cause = 'unproven_input_object'
        if cause:
            affected = [value for inputs in actuals.values() for value in inputs]
            self.add_boundary('container_return_unproven', node, env, affected,
                              call_id=call.id, detail=cause)
            if cause == 'container_return_budget':
                self.result.boundaries.append({'call_id': call.id, 'reason': cause})
            return None
        obj = values[0]
        return {'source': obj['source'], 'container_shape': obj['container_shape'],
                'parameter_container': obj.get('parameter_container'),
                'identity': 'argument_alias', 'parameter': fact['parameter'],
                'function': asdict(target[0]),
                'conditions': copy.deepcopy(fact.get('conditions', [])),
                'evidence': _unique([item for value in values
                                    for item in value.get('evidence', [])] +
                    [self.evidence_at(target[0], statement) for statement in fact['evidence']])}

    def materialize(self, values, env, visited=()):
        result = []
        for value in values:
            if value.get('container_object'):
                converted = self.container_values([value], allow_contained=True)[0]
                if converted['kind'] == 'container':
                    result.append(value)
                    value = converted
            if value['kind'] != 'container':
                result.append(value)
                continue
            # Stop object cycles without claiming their missing contents are empty.
            # 遇到对象环时停止展开，不据此断言缺失内容为空。
            if value['source'] in visited:
                continue
            for item in self.materialize(env.get(value['source'], []), env, visited + (value['source'],)):
                prefix = value.get('output_path', [])
                materialized = dict(item, relation='contained',
                    output_path=prefix + item.get('output_path', []),
                    evidence=item['evidence'] + value['evidence'])
                if item.get('excluded_paths'):
                    materialized['excluded_paths'] = [prefix + path
                                                      for path in item['excluded_paths']]
                result.append(materialized)
        return result

    def project(self, values, index, env):
        result = []
        for value in self.container_values(values):
            if value['kind'] == 'container':
                if (value['source'].startswith('$remainder_tuple:')
                        and (type(index) is not int or index < 0)):
                    self.result.boundaries.append({'function': asdict(self.ref),
                        'reason': 'container_projection_unproven',
                        'object_source': value['source']})
                    continue
                content = [item for item in env.get(value['source'], [])
                           if item.get('container_role') != 'key']
                if value.get('parameter_container') and index != '*':
                    for item in content:
                        if item.get('output_path') == ['*']:
                            if [index] in item.get('excluded_paths', []):
                                continue
                            projected = dict(
                                item, projection=item.get('projection', []) + [index])
                            projected.pop('output_path', None)
                            result.append(projected)
                        else:
                            result.extend(select_dependencies([item], [index]))
                else:
                    result.extend(select_dependencies(content, [index]))
            else:
                result.extend(select_dependencies([value], [index]))
        return result

    def unknown_container_contents(self, values, env):
        for reference in self.container_values(values):
            if reference.get('kind') != 'container' or reference['source'] not in env:
                continue
            source = reference['source']
            env[source + '$state'] = [{'kind': 'container_state', 'source': source,
                                       'contents_unknown': True}]
            env[source] = [dict(value, excluded_paths=[]) if value.get('excluded_paths') else value
                           for value in env[source]]
            env[source + '$keys'] = _unique([
                dict(marker, excluded_keys=[], presence_unconfirmed=True)
                for marker in env.get(source + '$keys', [])] +
                [{'kind': 'key', 'source': '*', 'key': '*'}])

    def exact_container(self, values, shapes, env):
        references = self.container_values(values)
        if (not references or not all(value.get('kind') == 'container'
                and value.get('container_shape') in shapes
                and value.get('relation') == 'direct' and not value.get('value_incomplete')
                and not value.get('projection') and not value.get('output_path')
                and value['source'] in env for value in references)
                or len({value['source'] for value in references}) != 1):
            return None
        return references[0]

    def container_endpoint(self, call, node, obj=None):
        value = {'kind': 'call_result', 'source': call.id, 'relation': 'direct',
                 'object_only': True, 'evidence': [self.evidence(node)],
                 'conditions': copy.deepcopy(self.conditions)}
        if obj is not None:
            value['container_object'] = obj
        return value

    def copy_container(self, values, shape, node, call, env):
        allowed = ('dict',) if shape == 'dict' else ('list', 'tuple')
        reference = self.exact_container(values, allowed, env)
        if (reference is None or any(marker.get('contents_unknown')
                for marker in env.get(reference['source'] + '$state', []))):
            self.add_boundary('container_copy_unproven', node, env, values,
                              call_id=call.id, detail='unproven_input_shape_identity_or_contents')
            return None
        source = reference['source']
        alias = shape == reference['container_shape'] == 'tuple'
        output = source if alias else '$copy:' + call.id
        if not alias:
            env[output] = copy.deepcopy(env.get(source, []))
            env[output + '$keys'] = copy.deepcopy(env.get(source + '$keys', []))
            env.pop(output + '$state', None)
        obj = {'source': output, 'container_shape': shape,
               'parameter_container': reference.get('parameter_container'),
               'identity': 'argument_alias' if alias else 'shallow_copy',
               'copied_from': source}
        result = self.container_endpoint(call, node, obj)
        result['evidence'] = _unique(reference['evidence'] + result['evidence'])
        call.result_sources = [result]
        # Contents are read through the object at each use, never through a stale
        # whole-input dependency. Nested container IDs remain shallow aliases.
        # 每次使用时读取当前容器内容；嵌套容器身份仍为浅层别名。
        call.return_dependencies = []
        roots, unknown = self.affected_values(values, env)
        effect = {'kind': 'container_copy', 'operation': 'copy',
                  'input_container': source, 'output_container': output,
                  'container_shape': shape, 'identity': obj['identity'],
                  'mapping': roots, 'status': 'unknown_source' if unknown else 'bounded',
                  'completion': 'normal_return',
                  'conditions': copy.deepcopy(self.conditions), 'evidence': self.evidence(node)}
        call.effects.append(effect)
        if shape == 'dict':
            self.mapping_effects.append(effect)
        return [result]

    def container_constructor(self, node, call, env, actuals):
        name = node.func.id
        if (name not in ('dict', 'list', 'tuple')
                or self.analyzer._builtin_name_status(self.ref, self.node, name, env) != 'confirmed_builtin'
                or len(node.args) != 1 or node.keywords or isinstance(node.args[0], ast.Starred)):
            return None
        values = actuals.get(0, [])
        result = self.copy_container(values, name, node, call, env)
        if result is None:
            return None
        call.target_status = 'local_container_protocol'
        call.binding_status = 'complete'
        for binding in call.parameter_bindings:
            binding.update(parameter='object', status='exact', destination_kind='parameter')
        for argument in call.argument_sources:
            argument['parameter'] = 'object'
        for flow in call.argument_flows + call.parameter_flows:
            flow['target_parameter'] = 'object'
        return result

    def mapping_key_state(self, reference, key, env):
        if key == '*' or any(marker.get('contents_unknown')
                for marker in env.get(reference['source'] + '$state', [])):
            return 'unknown'
        markers = env.get(reference['source'] + '$keys', [])
        if any(marker['key'] == key and not marker.get('presence_unconfirmed') for marker in markers):
            return 'present'
        if any(marker['key'] == key or marker['key'] == '*'
               and key not in marker.get('excluded_keys', []) for marker in markers):
            return 'unknown'
        return 'absent'

    def mapping_setdefault(self, node, receiver, call, env, actuals):
        reference = self.exact_container(receiver, ('dict',), env)
        literal = self.literal_fact(node.args[0], env)
        key = (literal['value'] if literal and literal['type'] in ('str', 'int')
               and literal['value'] != '*' else '*')
        if reference is None or key == '*':
            self.add_boundary('container_effect_unknown', node, env, receiver,
                              call_id=call.id, detail='setdefault_key_or_receiver_unproven')
            self.unknown_container_contents(receiver, env)
            return None
        source = reference['source']
        roots, unknown = self.mapping_affected_values(receiver, env)
        state = self.mapping_key_state(reference, key, env)
        call.argument_sources.append({'argument': 'receiver', 'parameter': 'self',
                                      'sources': copy.deepcopy(self.materialize(receiver, env))})
        existing = self.project(receiver, key, env)
        default = actuals.get(1, [])
        previous, inserted = [], []
        present = {'mapping_membership': {'object_source': source, 'element_path': [key],
                                          'state': 'present'}, 'evidence': self.evidence(node)}
        absent = {'mapping_membership': {'object_source': source, 'element_path': [key],
                                         'state': 'absent'}, 'evidence': self.evidence(node)}
        if state != 'absent':
            previous = self.marked(existing, node)
            if state == 'unknown':
                previous = [dict(value, conditions=value.get('conditions', []) + [present])
                            for value in previous]
        if state != 'present':
            inserted = self.marked(default, node)
            if state == 'unknown':
                inserted = [dict(value, conditions=value.get('conditions', []) + [absent])
                            for value in inserted]
            # Separate this slot from the open remainder, retaining both guarded
            # existing/default alternatives instead of overriding an unknown key.
            # 将该槽位与开放余项分开，保留受条件约束的已有值和默认值候选。
            remainder = []
            for value in env.get(source, []):
                path = value.get('output_path', [])
                if path and path[0] == key:
                    continue
                if path and path[0] == '*':
                    value = dict(value, excluded_paths=_unique(value.get('excluded_paths', []) + [[key]]))
                remainder.append(value)
            slot = previous + inserted
            env[source] = remainder + [dict(value, output_path=[key] + value.get('output_path', []))
                                       for value in slot]
            markers = []
            for marker in env.get(source + '$keys', []):
                if marker['key'] == key:
                    continue
                if marker['key'] == '*':
                    marker = dict(marker, excluded_keys=_unique(marker.get('excluded_keys', []) + [key]))
                markers.append(marker)
            env[source + '$keys'] = markers + [{'kind': 'key', 'source': repr(key), 'key': key}]
            call.mutation_flows.extend(dict(value, target_container=source,
                effect_summary='mapping_setdefault') for value in self.materialize([
                    dict(value, output_path=[key] + value.get('output_path', [])) for value in inserted], env))
        effect = {'kind': 'mapping_element', 'operation': 'setdefault', 'mapping': roots,
                  'object_source': source, 'element_path': [key], 'state_before': state,
                  'state_after': 'conditional' if self.conditions else 'present',
                  'insertion': 'never' if state == 'present' else 'always' if state == 'absent' else 'conditional',
                  'status': 'bounded', 'completion': 'normal_return',
                  'conditions': copy.deepcopy(self.conditions), 'evidence': self.evidence(node)}
        self.mapping_effects.append(effect)
        call.effects.append(effect)
        selected = previous + inserted
        obj = self.exact_container(selected, ('dict', 'list', 'tuple', 'set'), env)
        endpoint = self.container_endpoint(call, node,
            {'source': obj['source'], 'container_shape': obj['container_shape'],
             'parameter_container': obj.get('parameter_container'), 'identity': 'element_alias'} if obj else None)
        endpoint['evidence'] = _unique(endpoint['evidence'] + [span for value in selected
                                                              for span in value.get('evidence', [])])
        call.return_dependencies = []
        call.result_sources = [endpoint] if obj else [endpoint] + selected
        return call.result_sources

    def inherited_setdefault(self, node, receiver, call, env):
        if (not isinstance(node.func, ast.Attribute) or node.func.attr != 'setdefault'
                or node.keywords or any(isinstance(item, ast.Starred) for item in node.args)
                or getattr(self.node, 'decorator_list', [])):
            return
        contract = container_method_effect(node.func.attr, ('dict',), len(node.args))
        parameters = self.node.args.posonlyargs + self.node.args.args
        if (contract is None or not parameters or not receiver or not all(
                value['kind'] == 'parameter' and value['source'] == parameters[0].arg
                and value.get('relation') == 'direct' and not value.get('projection')
                and not value.get('output_path') for value in receiver)):
            return
        owner = self.ref.qualname.rpartition('.')[0]
        matches = self.analyzer._definition_index.find(self.ref.module, owner, kind='class')
        proof = self.analyzer._dict_method_binding(matches[0][0], 'setdefault') if len(matches) == 1 else None
        if proof is None:
            return
        if proof['status'] != 'source_bound':
            self.add_boundary(proof['reason'], node, env, receiver, call_id=call.id)
            return
        proof = dict(proof)
        proof['evidence'] = [self.evidence_at(ref, cls) for ref, cls in proof.pop('hierarchy')]
        proof['evidence'].append(self.evidence(node))
        call.receiver_type_evidence.append(proof)
        call.target_status = 'builtin_method_candidate'
        call.binding_status = 'complete'
        for index, argument in enumerate(call.argument_sources):
            argument['parameter'] = contract.parameters[index]
            call.parameter_bindings[index].update(parameter=contract.parameters[index],
                                                 status='exact', destination_kind='parameter')
        for value in call.argument_flows + call.parameter_flows:
            position = value['argument'].get('position')
            if position is not None:
                value['target_parameter'] = contract.parameters[position]
        call.argument_sources.append({'argument': {'receiver': True}, 'parameter': 'self',
                                      'sources': self.materialize(receiver, env)})
        call.parameter_bindings.append({'argument': {'receiver': True}, 'parameter': 'self',
            'status': 'exact', 'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter'})
        key = node.args[0].value if isinstance(node.args[0], ast.Constant) and isinstance(
            node.args[0].value, (str, int)) else '*'
        roots, _ = self.affected_values(receiver, env)
        effect = {'kind': 'mapping_element', 'operation': 'setdefault', 'mapping': roots,
                  'element_path': [key], 'state_before': 'unknown', 'state_after': 'conditional',
                  'insertion': 'conditional', 'status': 'unknown_key' if key == '*' else 'source_candidate',
                  'completion': 'normal_return', 'conditions': copy.deepcopy(self.conditions),
                  'evidence': self.evidence(node), 'method_binding': copy.deepcopy(proof)}
        call.effects.append(effect)
        self.mapping_effects.append(effect)
        self.add_boundary('dynamic_method_override_possible', node, env, receiver, call_id=call.id)
        if key == '*':
            self.add_boundary('container_effect_unknown', node, env, receiver,
                              call_id=call.id, detail='dynamic_key_protocol_unconfirmed')

    def container_call(self, node, receiver, call, env, actuals=None):
        receiver = self.container_values(receiver)
        if (not isinstance(node.func, ast.Attribute) or not receiver or not all(
                v['kind'] == 'container' and v.get('relation') == 'direct'
                and not v.get('value_incomplete') and not v.get('projection')
                and not v.get('output_path') for v in receiver)):
            return None
        shapes = {v['container_shape'] for v in receiver}
        method = node.func.attr
        effect = container_method_effect(method, shapes, len(node.args))
        update_keywords = (method == 'update'
                           and all(keyword.arg is not None
                                   for keyword in node.keywords))
        if (effect is None or (node.keywords and not update_keywords)
                or any(isinstance(a, ast.Starred) for a in node.args)):
            self.result.boundaries.append({'call_id': call.id, 'callee_name': call.callee_name,
                                           'reason': 'container_effect_unknown'})
            return None
        if self.context_execution:
            safe = method in ('clear', 'copy') and not node.args
            if method in ('pop', 'get', 'setdefault') and shapes == {'dict'} and node.args:
                key = self.literal_fact(node.args[0], env)
                safe = bool(key and key['type'] in ('str', 'int') and key['value'] != '*')
            if method == 'update':
                safe = all(self.exact_container((actuals or {}).get(index, []), ('dict',), env)
                           for index in range(len(node.args)))
                safe = safe and all(isinstance(key, (str, int)) for argument in node.args
                    if isinstance(argument, ast.Dict) for key in [
                        item.value if isinstance(item, ast.Constant) else None for item in argument.keys])
            safe = safe and not any(isinstance(child, ast.Call) for argument in
                node.args + [keyword.value for keyword in node.keywords] for child in ast.walk(argument))
            if not safe:
                self.add_boundary('context_exit_data_protocol_unmodeled', node, env,
                                  call_id=call.id, affected_scope='unknown')
        call.target_status = 'local_container_protocol'
        call.binding_status = 'complete'
        if effect.mutates_receiver:
            self.invalidate_literals(receiver, env)
        parameters = effect.parameters
        for index, argument in enumerate(call.argument_sources):
            parameter = (parameters[index] if index < len(parameters)
                         else 'other' if method == 'update' else None)
            argument['parameter'] = parameter
            if (method == 'update'
                    and isinstance(argument.get('argument'), dict)
                    and argument['argument'].get('keyword') is not None):
                argument['target_path'] = [argument['argument']['keyword']]
            call.parameter_bindings[index].update(
                parameter=parameter, status='exact',
                destination_kind='parameter')
            if argument.get('target_path'):
                call.parameter_bindings[index]['target_path'] = argument['target_path']
        for flow in call.argument_flows + call.parameter_flows:
            slot = flow['argument']
            if 'position' in slot:
                flow['target_parameter'] = (parameters[slot['position']]
                                            if slot['position'] < len(parameters)
                                            else 'other')
            elif method == 'update' and slot.get('keyword') is not None:
                flow['target_parameter'] = 'other'
                flow['target_path'] = [slot['keyword']]
        if method == 'copy':
            return self.copy_container(receiver, 'dict', node, call, env)
        if method == 'setdefault':
            return self.mapping_setdefault(node, receiver, call, env, actuals or {})
        if method == 'get':
            index = node.args[0].value if isinstance(node.args[0], ast.Constant) else '*'
            known = all(self.mapping_key_state(value, index, env) == 'present'
                        for value in receiver)
            call.argument_sources.append({'argument': 'receiver', 'parameter': 'self',
                                          'sources': self.materialize(receiver, env)})
            call.result_sources = self.marked(
                self.project(receiver, index, env), node)
            call.return_dependencies = [{'kind': 'parameter', 'source': 'self',
                'projection': [index], 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            if len(node.args) == 2 and not known:
                call.return_dependencies.append({'kind': 'parameter', 'source': 'default',
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)})
            return None  # Preserve the call-result endpoint as well as its dependencies.
        if method == 'pop':
            requested = -1 if shapes == {'list'} else '*'
            if node.args:
                try:
                    requested = ast.literal_eval(node.args[0])
                except (ValueError, TypeError):
                    requested = '*'
                if (shapes == {'list'} and not isinstance(requested, int)):
                    requested = '*'
                if (shapes == {'dict'} and not isinstance(requested, (str, int))):
                    requested = '*'
            index = requested
            valid_index = True
            if (shapes == {'list'} and requested != '*'
                    and len({value['source'] for value in receiver}) == 1):
                reference = receiver[0]
                keys = [key['key'] for key in env.get(reference['source'] + '$keys', [])]
                if keys == list(range(len(keys))):
                    try:
                        index = list(range(len(keys)))[requested]
                    except IndexError:
                        valid_index = False
            call.argument_sources.append({'argument': 'receiver', 'parameter': 'self',
                                          'sources': copy.deepcopy(self.materialize(receiver, env))})
            if not valid_index:
                return []
            call.return_dependencies = [{'kind': 'parameter', 'source': 'self',
                'projection': [index], 'relation': 'direct',
                'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            call.result_sources = self.marked(
                self.project(receiver, index, env), node)
            if shapes == {'dict'} and len(node.args) == 2:
                call.return_dependencies.append({
                    'kind': 'parameter', 'source': 'default',
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)})
            if index != '*' and len({v['source'] for v in receiver}) == 1:
                for ref in receiver:
                    keys = [key['key'] for key in env.get(ref['source'] + '$keys', [])]
                    remaining = []
                    for value in env.get(ref['source'], []):
                        path = value.get('output_path', [])
                        if path and path[0] == index:
                            continue
                        if (shapes == {'list'} and path
                                and isinstance(path[0], int) and path[0] > index):
                            value = dict(value, output_path=[path[0] - 1] + path[1:])
                        elif shapes == {'dict'} and path and path[0] == '*':
                            value = dict(value, excluded_paths=_unique(
                                value.get('excluded_paths', []) + [[index]]),
                                conditions=value.get('conditions', []) +
                                           list(self.conditions))
                        remaining.append(value)
                    env[ref['source']] = remaining
                    if shapes == {'list'}:
                        env[ref['source'] + '$keys'] = [
                            {'kind': 'key', 'source': repr(position), 'key': position}
                            for position in range(len(keys) - 1)]
                    else:
                        markers = []
                        for marker in env.get(ref['source'] + '$keys', []):
                            if marker['key'] == index:
                                continue
                            if marker['key'] == '*':
                                marker = dict(marker, excluded_keys=_unique(
                                    marker.get('excluded_keys', []) + [index]))
                            markers.append(marker)
                        env[ref['source'] + '$keys'] = markers
            if shapes == {'dict'}:
                roots, unknown = self.affected_values(receiver, env)
                mapping_effect = {
                    'operation': 'pop', 'mapping': roots,
                    'element_path': [index],
                    'state_after': ('conditional' if self.conditions
                                    else 'absent' if index != '*' else 'unknown'),
                    'status': 'unknown_key' if index == '*' or unknown else 'bounded',
                    'conditions': list(self.conditions),
                    'evidence': self.evidence(node)}
                self.mapping_effects.append(mapping_effect)
                call.effects.append(dict(mapping_effect, kind='mapping_element'))
            return None
        if method == 'update':
            roots, unknown = self.affected_values(receiver, env)
            paths = []
            inserted = []
            for argument in call.argument_sources:
                slot = argument.get('argument', {})
                explicit_key = (slot.get('keyword')
                                if isinstance(slot, dict) else None)
                for value in argument.get('sources', []):
                    path = ([explicit_key] if explicit_key is not None else
                            value.get('output_path', ['*']))
                    if not path:
                        path = ['*']
                    paths.append(path)
                    inserted.append(dict(value, output_path=path,
                                         conditions=value.get('conditions', []) +
                                                    list(self.conditions)))
            for ref in receiver:
                previous = list(env.get(ref['source'], []))
                for path in paths:
                    if path and path[0] != '*':
                        updated = []
                        for value in previous:
                            old_path = value.get('output_path', [None])
                            if old_path[0] == path[0]:
                                continue
                            if old_path[0] == '*':
                                value = dict(value, excluded_paths=_unique(
                                    value.get('excluded_paths', []) + [[path[0]]]))
                            updated.append(value)
                        previous = updated
                env[ref['source']] = _loop_env(
                    {'items': previous + inserted})['items']
                markers = list(env.get(ref['source'] + '$keys', []))
                for path in paths:
                    key = path[0] if path else '*'
                    markers.append({'kind': 'key', 'source': repr(key), 'key': key})
                env[ref['source'] + '$keys'] = _unique(markers)
                call.mutation_flows.extend(
                    dict(value, target_container=ref['source'],
                         effect_summary='mapping_update')
                    for value in inserted)
            mapping_effect = {
                'operation': 'update', 'mapping': roots,
                'element_path': (paths[0] if len(paths) == 1 else ['*']),
                'state_after': ('conditional' if self.conditions else
                                'present' if paths and all(path[0] != '*'
                                                          for path in paths)
                                else 'unknown'),
                'status': 'unknown_source' if unknown or not paths else 'bounded',
                'conditions': list(self.conditions),
                'evidence': self.evidence(node)}
            self.mapping_effects.append(mapping_effect)
            call.effects.append(dict(mapping_effect, kind='mapping_element'))
            return None
        for ref in receiver:
            if method == 'clear':
                if len({v['source'] for v in receiver}) == 1:
                    env[ref['source']] = []
                    env[ref['source'] + '$keys'] = []
                    env.pop(ref['source'] + '$state', None)
            else:
                values = self.marked(call.argument_sources[0]['sources'], node)
                inserted = [dict(v, output_path=['*'] + v.get('output_path', [])) for v in values]
                env[ref['source']] = _loop_env({'items': env.get(ref['source'], []) + inserted})['items']
                env[ref['source'] + '$keys'] = [{'kind': 'key', 'source': '*', 'key': '*'}]
                call.mutation_flows.extend(dict(v, target_container=ref['source']) for v in inserted)
        if method == 'clear':
            roots, unknown = self.mapping_affected_values(receiver, env)
            call.effects.append({'kind': 'container_clear', 'operation': 'clear',
                'mapping': roots, 'element_path': [],
                'object_sources': _unique(value['source'] for value in receiver),
                'completion': 'normal_return', 'status': 'unknown' if unknown else 'exact',
                'conditions': copy.deepcopy(self.conditions), 'evidence': self.evidence(node)})
        return None  # Preserve the mutator's call-result endpoint (the runtime value is None).
