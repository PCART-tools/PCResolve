## @package pcresolve.flow.transfer.summary_values
## @brief Values operations for query-local flow summaries.

import ast
import copy
from dataclasses import asdict
from pcresolve.flow.model.results import FunctionRef
from pcresolve.flow.proofs.callables.dispatch.finite_dispatch import (
    DispatchLimit,
    generated_dict,
)
from pcresolve.flow.transfer._summary_support import _class_lookup_key, _unique
from pcresolve.flow.transfer.recursive_summary import (
    create_child_summary, evaluate_child_expression,
)


class ValuesMixin:
    def callable_targets(self, values):
        if len(values) > 64:
            self.result.boundaries.append({'function': asdict(self.ref),
                                           'reason': 'callable_candidate_budget'})
            return [], False
        targets, complete = [], bool(values)
        for value in values:
            identity = value.get('callable_type')
            if value.get('kind') == 'callable':
                matches = self.analyzer._definition_index.find(
                    value.get('module', self.ref.module), value['source'])
                identity = asdict(matches[0][0]) if len(matches) == 1 else None
            if not identity or value.get('relation') != 'direct' or any(
                    value.get(flag) for flag in ('projection', 'output_path',
                        'import_modified', 'import_incomplete')):
                complete = False
                continue
            key = identity['module'], identity['qualname']
            if key in self.modified_return_callables:
                complete = False
                continue
            matches = self.analyzer._definition_index.find(*key)
            if len(matches) != 1 or ('.' not in key[1]
                    and not self.analyzer._stable_import_name('.'.join(key))):
                complete = False
                continue
            targets.append(matches[0])
            complete = complete and not value.get('value_incomplete')
        return _unique(targets), complete

    def literal_fact(self, node, env):
        if isinstance(node, ast.Name):
            values = env.get(node.id, [])
            facts = [value.get('literal') for value in values]
            return facts[0] if facts and all(fact == facts[0] and fact is not None
                and not value.get('value_incomplete')
                and value.get('relation') == 'direct'
                and not value.get('projection') and not value.get('output_path')
                for fact, value in zip(facts, values)) else None
        if node is None or sum(1 for _ in ast.walk(node)) > 128:
            return None
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError):
            return None
        if type(value) is float and not abs(value) < float('inf'):
            return None
        if type(value) in (str, int, float, bool, type(None)):
            return {'type': type(value).__name__, 'value': value}
        if type(value) in (tuple, list) and len(value) <= 64 and all(
                type(item) in (str, int, float, bool, type(None))
                and (type(item) is not float or abs(item) < float('inf')) for item in value):
            return {'type': type(value).__name__, 'value': list(value)}
        return None

    def invalidate_literals(self, values, env):
        identities = {value['source'] for value in self.container_values(values)
                      if value.get('kind') == 'container'}
        for name, items in env.items():
            env[name] = [{key: item for key, item in value.items() if key != 'literal'}
                         if value.get('source') in identities else value for value in items]

    def module_dispatch(self, name, env):
        if name in env:
            return env[name]
        bodies = self.analyzer.module_bodies.get(self.ref.module, [])
        facts = self.analyzer.import_binding_facts.get(self.ref.module, [])
        if len(bodies) != 1 or len(facts) != 1:
            return []
        statements = facts[0].get(name, [])
        if len(statements) != 1 or not isinstance(statements[0], ast.Assign):
            return []
        assignment = statements[0]
        expression = assignment.value
        if isinstance(expression, ast.DictComp):
            ## Check that a generated table entry names one stable source function.
            ## 检查生成表项是否指向唯一稳定的源码函数。
            #
            #  @param symbol Candidate function name.
            #  @return True only for a supported stable definition.
            def stable_function(symbol):
                matches = self.analyzer._definition_index.find(self.ref.module, symbol)
                return (len(matches) == 1 and not matches[0][1].decorator_list
                    and matches[0][0].lineno < expression.lineno
                    and '.' not in symbol and self.analyzer._stable_import_name(
                        self.ref.module + '.' + symbol))
            try:
                expression = generated_dict(expression, bodies[0][1], facts[0], stable_function)
            except DispatchLimit:
                self.add_boundary('generated_dispatch_budget', assignment, env)
                return []
        if (assignment not in bodies[0][1] or len(assignment.targets) != 1
                or not isinstance(expression, ast.Dict)
                or any(not isinstance(key, ast.Constant) or not isinstance(key.value, str)
                       for key in expression.keys)):
            return []
        if len(expression.keys) > 64:
            self.add_boundary('literal_dispatch_budget', assignment, env)
            return []
        # Any use other than a read-only subscript can invalidate the closed table.
        # 只读下标以外的使用可能使封闭表假设失效。
        for statement in bodies[0][1]:
            for parent in ast.walk(statement):
                for child in ast.iter_child_nodes(parent):
                    if isinstance(child, ast.Name) and child.id == name and isinstance(child.ctx, ast.Load):
                        if not (isinstance(parent, ast.Subscript) and parent.value is child
                                and isinstance(parent.ctx, ast.Load)):
                            return []
        module_ref = FunctionRef(self.ref.module, '', bodies[0][0], 0)
        summary = create_child_summary(self._make_child_summary, self.result,
                                       module_ref, self.node, self.remaining)
        module_env = {}
        execution = evaluate_child_expression(summary, expression, module_env)
        env.update(execution.heap_updates)
        self.remaining = execution.remaining
        return self.marked(execution.values, assignment)

    def class_value(self, class_ref, node, env):
        value = {'kind': 'class', 'module': class_ref.module,
                'source': class_ref.qualname, 'class_type': asdict(class_ref),
                'source_class_origin': {'basis': 'source_symbol', 'class': asdict(class_ref),
                    'evidence': [self.evidence(node)], 'call_context': []},
                'relation': 'direct', 'evidence': [self.evidence(node)],
                'conditions': list(self.conditions)}
        if self.class_origin_invalid(asdict(class_ref), env):
            value['value_incomplete'] = True
        effects = self.class_lookup_effects(asdict(class_ref), env)
        if effects:
            value['class_lookup_mutations'] = copy.deepcopy(effects)
        return value

    def class_values(self, values, allow_incomplete=False, env=None):
        known = []
        for value in values:
            if (value.get('relation') != 'direct' or value.get('projection')
                    or value.get('output_path') or value.get('import_modified')
                    or value.get('import_incomplete')
                    or value.get('value_incomplete') and not allow_incomplete):
                return []
            if value.get('kind') == 'class' or value.get('class_type'):
                identity = value.get('class_type')
                matches = self.analyzer._definition_index.find(
                    identity['module'] if identity else value['module'],
                    identity['qualname'] if identity else value['source'], kind='class')
                if len(matches) != 1:
                    return []
                known.append(dict(value, kind='class', module=matches[0][0].module,
                                  source=matches[0][0].qualname,
                                  class_type=asdict(matches[0][0])))
            elif value.get('kind') == 'import':
                target = self.analyzer._class_symbol(value['source'])
                if target is None:
                    return []
                known.append(dict(value, kind='class', module=target[0].module,
                                  source=target[0].qualname,
                                  class_type=asdict(target[0])))
            elif value.get('kind') == 'call_result':
                call = next((call for call in self.calls if call.id == value['source']), None)
                if call is None or call.target is None:
                    return []
                matches = self.analyzer._definition_index.find(
                    call.target.module, call.target.qualname)
                definition = next((item for item in matches if item[0] == call.target), None)
                if definition is None:
                    return []
                definition = self.analyzer._selected_definition(
                    definition, self.analyzer._incoming_facts(definition, call))
                returned, cause = self.analyzer._class_returns(
                    definition, self.analyzer._receiver_class(definition, call),
                    self.analyzer._incoming_facts(definition, call))
                if cause:
                    self.result.boundaries.append({'call_id': call.id,
                        'reason': cause, 'callee_name': call.callee_name})
                if not returned:
                    return []
                returned = [dict(item,
                    evidence=item.get('evidence', []) + value.get('evidence', []),
                    conditions=item.get('conditions', []) + value.get('conditions', []))
                    for item in returned]
                call.result_sources = _unique(call.result_sources + returned)
                if not allow_incomplete and any(value.get('value_incomplete') for value in returned):
                    return []
                known.extend(returned)
            else:
                return []
        if env is not None:
            for value in known:
                effects = self.class_lookup_effects(value['class_type'], env)
                if effects:
                    value['class_lookup_mutations'] = _unique(
                        value.get('class_lookup_mutations', []) + copy.deepcopy(effects))
                if self.class_origin_invalid(value['class_type'], env):
                    value['value_incomplete'] = True
        return _unique(known)

    def attribute_key(self, node, env):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            return None
        values = self.class_values(env.get(node.value.id, []), env=env)
        identities = _unique([value['class_type'] for value in values])
        if len(identities) != 1:
            return None
        identity = identities[0]
        hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
        if hierarchy is None or any(cls.decorator_list or cls.keywords for _, cls in hierarchy):
            return None
        if any(self.analyzer._definition_index.find(ref.module, ref.qualname + '.' + node.attr)
               for ref, _ in hierarchy):
            return None
        attribute = node.attr
        owner = self.ref.qualname.rpartition('.')[0].rpartition('.')[2].lstrip('_')
        if attribute.startswith('__') and not attribute.endswith('__') and owner:
            attribute = '_' + owner + attribute
        return '$attribute:%s:%s:%s' % (identity['module'], identity['qualname'], attribute), identity

    def invalidate_attributes(self, env):
        for key in list(env):
            if key.startswith('$attribute:'):
                env[key] = []

    def class_lookup_effects(self, identity, env):
        hierarchy = self.analyzer._class_mro(identity['module'], identity['qualname'])
        owners = [asdict(ref) for ref, _ in hierarchy] if hierarchy else [identity]
        return _unique([effect for owner in owners for effect in env.get(_class_lookup_key(owner), [])])

    def register_class_lookup_effect(self, effect, env):
        key = _class_lookup_key(effect['receiver_class'])
        env[key] = _unique(env.get(key, []) + [copy.deepcopy(effect)])
        for name, values in list(env.items()):
            updated = []
            for value in values:
                identity = value.get('class_type') or value.get('instance_type')
                effects = self.class_lookup_effects(identity, env) if identity else []
                updated.append(dict(value, class_lookup_mutations=_unique(
                    value.get('class_lookup_mutations', []) + copy.deepcopy(effects)))
                    if effects else value)
            env[name] = updated

    def class_lookup_affected(self, values, attributes):
        return any(set(effect.get('attributes', [])) & set(attributes)
                   for value in values for effect in value.get('class_lookup_mutations', []))
