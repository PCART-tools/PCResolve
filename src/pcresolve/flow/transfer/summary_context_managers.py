## @package pcresolve.flow.transfer.summary_context_managers
## @brief Context Managers operations for query-local flow summaries.

import ast
import copy
from dataclasses import asdict
from pcresolve.facts.effect_facts import contains_yield
from pcresolve.facts.program_facts import FunctionSignature, bind_ast_call
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.flow.model.results import FlowAnalysis, FunctionRef
from pcresolve.flow.proofs.protocols._contextmanager_instance_effects import (
    temporary_receiver_attributes as bounded_temporary_receiver_attributes,
)
from pcresolve.flow.transfer._summary_support import (
    _CONTEXT_EXIT_PATH_LIMIT,
    _CONTEXT_PROTOCOL_NODE_LIMIT,
    _call_key,
    _exception_class,
    _may_raise,
    _unique,
)
from pcresolve.flow.transfer.environment import merge_environments as _merge_env


class ContextManagersMixin:
    def block(self, statements, env):
        # Exit tuples carry pending returns through finally without committing
        # them to the function summary prematurely.
        active = [env]
        exits = []
        for node in statements:
            if not active:
                break
            current = _merge_env(active)
            outcomes = self.statement(node, current)
            active = [e for kind, e, _, _ in outcomes if kind == 'normal']
            exits.extend(o for o in outcomes if o[0] != 'normal')
        exits.extend(('normal', e, [], None) for e in active)
        return exits

    def context_protocol(self, values, method):
        identities = _unique([value.get('instance_type') for value in values])
        if (not values or len(identities) != 1 or not identities[0]
                or any(value.get('value_incomplete') or value.get('relation') != 'direct'
                       or value.get('projection') or value.get('output_path') for value in values)):
            return None, None, ['receiver_unconfirmed']
        receiver = FunctionRef(**identities[0])
        hierarchy = self.analyzer._class_mro(receiver.module, receiver.qualname)
        if hierarchy is None:
            return None, receiver, ['mro_unavailable']
        if any(cls.decorator_list or cls.keywords or any(
                name in statement_scope_facts(cls.body).bound
                for name in ('__getattribute__', '__getattr__', '__setattr__',
                             '__delattr__', '__init_subclass__'))
                for _, cls in hierarchy):
            return None, receiver, ['lookup_customization']
        pending = [member for _, cls in hierarchy for member in cls.body
                   if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and member.name in ('__init__', '__new__', '__enter__')]
        visited, steps = set(), 0
        while pending:
            member = pending.pop()
            if id(member) in visited:
                continue
            visited.add(id(member))
            positional = member.args.posonlyargs + member.args.args
            aliases = {positional[0].arg} if positional else set()
            for child in ast.walk(member):
                steps += 1
                if self.analyzer._analysis_budget is not None:
                    self.analyzer._analysis_budget.checkpoint()
                if steps > _CONTEXT_PROTOCOL_NODE_LIMIT:
                    return None, receiver, ['context_enter_budget']
                if isinstance(child, ast.Assign) and isinstance(child.value, ast.Name):
                    if child.value.id in aliases:
                        aliases.update(target.id for target in child.targets if isinstance(target, ast.Name))
                if (isinstance(child, ast.Attribute) and child.attr == '__class__'
                        and isinstance(child.ctx, (ast.Store, ast.Del))):
                    return None, receiver, ['instance_class_write']
                if isinstance(child, ast.Call) and isinstance(child.func, (ast.Name, ast.Attribute)):
                    mutator = child.func.id if isinstance(child.func, ast.Name) else child.func.attr
                    if mutator in ('setattr', 'delattr', '__setattr__', '__delattr__'):
                        bound = (mutator.startswith('__') and isinstance(child.func, ast.Attribute)
                            and isinstance(child.func.value, ast.Name) and child.func.value.id in aliases)
                        key_index = 0 if bound else 1
                        if len(child.args) <= key_index or (not isinstance(child.args[key_index], ast.Constant)
                                or child.args[key_index].value == '__class__'):
                            return None, receiver, ['instance_class_write_unconfirmed']
                if (isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                        and isinstance(child.func.value, ast.Name) and child.func.value.id in aliases):
                    for _, cls in hierarchy:
                        helpers = [statement for statement in cls.body
                                   if child.func.attr in statement_scope_facts([statement]).bound]
                        if helpers:
                            pending.extend(statement for statement in helpers
                                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)))
                            break
        target = None
        for class_ref, cls in hierarchy:
            members = [statement for statement in cls.body
                       if method in statement_scope_facts([statement]).bound]
            if not members:
                continue
            if (len(members) != 1 or not isinstance(members[0], ast.FunctionDef)
                    or members[0].name != method or members[0].decorator_list
                    or contains_yield(members[0])):
                return None, receiver, ['descriptor_unconfirmed']
            matches = self.analyzer._definition_index.find(class_ref.module,
                class_ref.qualname + '.' + method)
            target = matches[0] if len(matches) == 1 and matches[0][1] is members[0] else None
            break
        if target is None:
            return None, receiver, ['definition_unavailable']
        writes, truncated = self.analyzer._class_binding_writes()
        if truncated:
            return None, receiver, ['class_binding_budget']
        classes = {(ref.module, ref.qualname) for ref, _ in hierarchy}
        if any((ref.module, ref.qualname) in classes and attribute in (
                method, '*', '__bases__', '__class__') for ref, attribute, _, _, _ in writes):
            return None, receiver, ['visible_protocol_write']
        return target, receiver, []

    def context_signature_valid(self, target, arguments):
        if target is None:
            return False
        call = ast.Call(func=ast.Name(id='$protocol', ctx=ast.Load()),
                        args=[ast.Constant(value=None) for _ in range(arguments + 1)], keywords=[])
        records, reasons = bind_ast_call(call, FunctionSignature.from_ast(target[1].args))
        return not reasons and all(record['status'] == 'exact' for record in records)

    def context_exit_noop(self, target):
        if not self.context_signature_valid(target, 3):
            return False
        for statement in target[1].body:
            if isinstance(statement, ast.Pass) or (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str)):
                continue
            if isinstance(statement, ast.Return) and (statement.value is None
                    or isinstance(statement.value, ast.Constant)
                    and statement.value.value in (None, False)):
                return True
            return False
        return True

    def unknown_context_effects(self, env):
        self.unknown_container_contents([value for items in env.values() for value in items], env)
        self.invalidate_attributes(env)
        for name, values in env.items():
            env[name] = [dict(value, value_incomplete=True, instance_candidates=[])
                         if value.get('instance_type') or value.get('instance_candidates')
                         or value.get('class_type') or value.get('callable_type') else value
                         for value in values]

    def apply_temporary_receiver_attributes(self, env, effect, entering):
        receiver = effect['receiver_parameter']
        expected = effect['receiver_origin']
        additions = set(effect['attributes'])
        prior = set(effect['prior_own_attributes'])
        updated = []
        for value in env.get(receiver, []):
            origin = value.get('fresh_receiver_origin')
            if (origin and origin.get('current_function') == expected.get('current_function')
                    and origin.get('allocation') == expected.get('allocation')):
                changed = copy.deepcopy(value)
                new_origin = copy.deepcopy(origin)
                own = set(origin.get('own_attributes', ()))
                new_origin['own_attributes'] = sorted(
                    own | additions if entering else own - additions | prior)
                changed['fresh_receiver_origin'] = new_origin
                updated.append(changed)
            else:
                updated.append(value)
        if updated:
            env[receiver] = _unique(updated)

    def context_truth(self, node, env):
        literal = self.literal_fact(node, env)
        if literal is not None:
            return bool(literal['value'])
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            truth = self.context_truth(node.operand, env)
            return not truth if truth is not None else None
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], (ast.Is, ast.IsNot))
                and len(node.comparators) == 1 and isinstance(node.comparators[0], ast.Constant)
                and node.comparators[0].value is None and isinstance(node.left, ast.Name)):
            values = env.get(node.left.id, [])
            if values and all(value.get('kind') == 'context_exception' for value in values):
                return isinstance(node.ops[0], ast.IsNot)
            fact = self.literal_fact(node.left, env)
            if fact is not None:
                equal = fact['value'] is None
                return equal if isinstance(node.ops[0], ast.Is) else not equal
        return None

    def context_operation_exits(self, node, previous, env, exceptional=None):
        receiver, key = None, None
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'pop' and len(node.args) == 1):
            receiver, key = node.func.value, node.args[0]
        elif isinstance(node, ast.Subscript):
            receiver, key = node.value, node.slice
        if receiver is None:
            if isinstance(node, ast.Call):
                call = next((call for call in reversed(self.calls)
                             if call.id == _call_key(self.ref.file_path, node)), None)
                if call and call.target_status == 'local_container_protocol':
                    method = node.func.attr
                    if method in ('clear', 'copy', 'update') or (
                            method == 'pop' and len(node.args) == 2):
                        return [], True
            return exceptional or [], True
        reference = (self.exact_container(previous.get(receiver.id, []), ('dict',), previous)
                     if isinstance(receiver, ast.Name) else None)
        literal = self.literal_fact(key, previous)
        if reference is None or literal is None or literal['type'] not in ('str', 'int'):
            self.add_boundary('context_exit_data_protocol_unmodeled', node, env, affected_scope='unknown')
            return [('raise', previous, [], None)], True
        state = self.mapping_key_state(reference, literal['value'], previous)
        return ([] if state == 'present' else [('raise', previous, [], 'KeyError')], state != 'absent')

    def execute_context_exit(self, target, call, state):
        if target is None or call.binding_status != 'complete':
            return None, ['context_exit_binding_unconfirmed']
        ref, method = target
        if ref in self.analyzer._context_exit_stack or len(self.analyzer._context_exit_stack) >= 8:
            return None, ['context_exit_recursion']
        steps = 0
        for _ in ast.walk(method):
            steps += 1
            if self.analyzer._analysis_budget is not None:
                self.analyzer._analysis_budget.checkpoint()
            if steps > min(self.analyzer._fact_calls, _CONTEXT_PROTOCOL_NODE_LIMIT):
                break
        if self.analyzer._fact_functions <= 0 or steps > min(
                self.analyzer._fact_calls, _CONTEXT_PROTOCOL_NODE_LIMIT):
            return None, ['context_exit_budget']
        self.analyzer._fact_functions -= 1
        self.analyzer._fact_calls -= steps
        frame = {key: copy.deepcopy(values) for key, values in state.items() if key.startswith('$')}
        parameters = method.args.posonlyargs + method.args.args + method.args.kwonlyargs
        for parameter in parameters:
            sources = [value for argument in call.argument_sources
                       if argument.get('parameter') == parameter.arg for value in argument['sources']]
            literals = [argument.get('literal') for argument in call.argument_sources
                        if argument.get('parameter') == parameter.arg]
            if literals and all(literal is not None and literal == literals[0] for literal in literals):
                sources = [dict(value, literal=copy.deepcopy(literals[0])) for value in sources] or [
                    {'kind': 'context_data', 'source': call.id, 'relation': 'direct',
                     'literal': copy.deepcopy(literals[0]), 'evidence': [], 'conditions': []}]
            frame[parameter.arg] = copy.deepcopy(sources)
        if parameters:
            frame[parameters[0].arg] = copy.deepcopy(call._context_manager_values)
        if method.args.vararg:
            actual = [argument for argument in call.argument_sources
                      if argument.get('parameter') == method.args.vararg.arg]
            heap = '$context_arguments:' + call.id
            frame[heap] = [dict(value, output_path=argument.get('target_path', [])
                               + value.get('output_path', []))
                           for argument in actual for value in argument['sources']]
            frame[heap + '$keys'] = [{'kind': 'key', 'source': index, 'key': index}
                                    for index in range(len(actual))]
            frame[method.args.vararg.arg] = [{'kind': 'container', 'source': heap,
                'container_shape': 'tuple', 'relation': 'direct', 'evidence': [], 'conditions': []}]
        captures = self.analyzer._captures(ref, method)
        for capture in captures:
            frame[capture] = copy.deepcopy(state.get(capture, []))
        for local in self.analyzer._scope_facts(method).bound:
            frame.setdefault(local, [])
        scratch = FlowAnalysis(ref, {})
        child = self._make_child_summary(scratch, ref, method, self.remaining)
        child.context_execution = True
        child.context_cleanup_order = self.context_cleanup_order
        child.conditions = copy.deepcopy(self.conditions)
        self.analyzer._context_exit_stack.append(ref)
        try:
            outcomes = child.block(method.body, frame)
        finally:
            self.analyzer._context_exit_stack.pop()
        self.remaining = min(self.remaining, child.remaining)
        self.calls.extend(child.calls)
        self.mapping_effects.extend(child.mapping_effects)
        self.result.boundaries.extend(scratch.boundaries)
        supported = set()
        for source_call in child.calls:
            if source_call.target_status == 'local_container_protocol':
                supported.add(source_call.id)
            elif (source_call.target_status == 'builtin_boundary'
                    and _exception_class(source_call.callee_name) is not None
                    and self.analyzer._builtin_name_status(ref, method, source_call.callee_name)
                        == 'confirmed_builtin' and all(
                            argument.get('literal') is not None for argument in source_call.argument_sources)):
                supported.add(source_call.id)
        issues = [boundary['reason'] for boundary in scratch.boundaries if not (
            boundary.get('call_id') in supported and boundary['reason'] == 'builtin_boundary')]
        if any(source_call.id not in supported for source_call in child.calls):
            issues.append('context_exit_call_unmodeled')
        if any(kind == 'unknown' for kind, _, _, _ in outcomes):
            issues.append('context_exit_completion_unresolved')
        if issues:
            return None, _unique(issues)
        call.effects = _unique([dict(effect, exit_call_id=call.id,
            completion=effect.get('completion', 'normal_return'),
            conditions=_unique(effect.get('conditions', []) + self.conditions))
            for source_call in child.calls for effect in source_call.effects]
            + [dict(effect, exit_call_id=call.id, completion='normal_return')
               for effect in child.mapping_effects])
        completed = []
        nonlocals = self.analyzer._scope_facts(method).nonlocals
        for kind, frame_state, values, payload in outcomes:
            updated = copy.deepcopy(state)
            updated.update({key: copy.deepcopy(values) for key, values in frame_state.items()
                            if key.startswith('$') or key in nonlocals})
            completed.append((kind, updated, values, payload))
        return completed, []

    def context_exit_call(self, node, record, outcome, origin):
        kind, state, values, exception = outcome
        target_ref = record['exit']['target']
        target = next((item for item in self.analyzer._definition_index.find(
            target_ref['module'], target_ref['qualname']) if asdict(item[0]) == target_ref), None
            ) if target_ref else None
        index = record['item_index']
        order = self.context_cleanup_order[0]
        self.context_cleanup_order[0] += 1
        proof = {'kind': 'context_manager_exit', 'method': '__exit__', 'lookup': 'type_mro',
            'with_id': record['with_id'], 'item_index': index, 'cleanup_order': order,
            'incoming_exit': {'kind': kind, 'exception': exception if kind == 'raise' else None,
                              'origin': origin},
            'basis': 'source_snapshot', 'runtime_target_confirmed': False,
            'assumptions': copy.deepcopy(record['assumptions']),
            'issues': copy.deepcopy(record['exit']['issues']),
            'context_expression': copy.deepcopy(record['context_expression'])}
        if kind == 'return':
            proof['pending_return_sources'] = copy.deepcopy(values)
        if target:
            proof['definition'] = self.evidence_at(*target)
            proof['source_hashes'] = {path: self.analyzer.hashes[path] for path in sorted(
                {self.ref.file_path, target[0].file_path}
                | set(record.get('source_hashes', {}))) if path in self.analyzer.hashes}
        temporary = '$with_exit:%s:%s' % (record['with_id'], order)
        arguments = [temporary + ':exc:%s' % index for index in range(3)]
        state[temporary] = copy.deepcopy(record['manager_sources']) if target else [
            dict(value, value_incomplete=True) for value in record['manager_sources']]
        for index, name in enumerate(arguments):
            state[name] = ([{'kind': 'context_exception', 'source': record['with_id'],
                'component': ('type', 'value', 'traceback')[index], 'exception': exception,
                'relation': 'direct', 'evidence': [], 'conditions': copy.deepcopy(self.conditions)}]
                if kind == 'raise' else [{'kind': 'context_data', 'source': record['with_id'],
                    'literal': {'type': 'NoneType', 'value': None}, 'relation': 'direct',
                    'evidence': [], 'conditions': copy.deepcopy(self.conditions)}])
            if kind == 'unknown':
                state[name] = [{'kind': 'context_data', 'source': record['with_id'],
                    'component': ('type', 'value', 'traceback')[index], 'value_incomplete': True,
                    'relation': 'direct', 'evidence': [], 'conditions': copy.deepcopy(self.conditions)}]
        implicit = ast.Call(func=ast.Attribute(value=ast.Name(id=temporary, ctx=ast.Load()),
            attr='__exit__', ctx=ast.Load()), args=[ast.Name(id=name, ctx=ast.Load()) for name in arguments],
            keywords=[])
        for child in ast.walk(implicit):
            ast.copy_location(child, node)
        implicit._flow_implicit_suffix = ':with_exit:%s:%s' % (record['item_index'], order)
        implicit._flow_implicit_protocol = proof
        implicit._flow_protocol_target = target
        implicit._flow_skip_effects = True
        self.expression(implicit, state)
        for name in [temporary] + arguments:
            state.pop(name, None)
        call = next((call for call in reversed(self.calls) if call.id == _call_key(self.ref.file_path, implicit)), None)
        record['exit'].setdefault('executions', []).append({'call_id': call.id if call else None,
            'cleanup_order': order, 'incoming_exit': copy.deepcopy(proof['incoming_exit'])})
        if call:
            call.callee_name = record['context_expression']['source_text'] + '.__exit__'
            call._context_manager_values = copy.deepcopy(record['manager_sources'])
            for boundary in self.result.boundaries:
                if boundary.get('call_id') == call.id and 'callee_name' in boundary:
                    boundary['callee_name'] = call.callee_name
        return target, call

    def cleanup_context_exits(self, node, outcomes, records, origin='body'):
        before = copy.deepcopy(self.conditions)
        for record in reversed(records):
            completed = []
            for outcome in outcomes:
                first_outcome = len(completed)
                kind, state, pending, exception = outcome
                self.conditions = _unique(before + record['conditions'])
                temporary_effect = record.get('bounded_temporary_receiver_effects')
                if temporary_effect is not None:
                    self.apply_temporary_receiver_attributes(state, temporary_effect,
                                                              entering=False)
                    record['exit'].setdefault('executions', []).append({
                        'call_id': None, 'cleanup_order': len(record['exit']['executions']),
                        'incoming_exit': {'kind': kind, 'exception': exception if kind == 'raise' else None,
                                          'origin': origin},
                        'status': 'source_modeled', 'issues': [],
                        'evidence': temporary_effect['evidence']})
                    completed.append((kind, state, pending, exception))
                    continue
                target, call = self.context_exit_call(node, record, outcome, origin)
                if call:
                    self.conditions.append({'context_exit': call.id, 'incoming_exit_kind': kind,
                                            'exception': exception if kind == 'raise' else None})
                executed, issues = ((None, ['context_exit_incoming_unresolved']) if kind == 'unknown' else
                    self.execute_context_exit(target, call, state) if call else
                    (None, ['context_exit_budget']))
                if executed is None:
                    self.add_boundary('context_exit_unmodeled', node, state,
                        [value for items in state.values() for value in items],
                        with_id=record['with_id'], item_index=record['item_index'],
                        call_id=call.id if call else None, exit_target=record['exit']['target'],
                        issues=issues, affected_scope='unknown', completion='unconfirmed')
                    for reason in ('context_exit_budget', 'context_exit_recursion'):
                        if reason in issues:
                            self.add_boundary(reason, node, state, call_id=call.id if call else None)
                    self.unknown_context_effects(state)
                    pending = [dict(value, value_incomplete=True, instance_candidates=[])
                               if any(value.get(key) for key in ('instance_type', 'instance_candidates',
                                   'class_type', 'callable_type')) or value.get('kind') == 'callable' else value
                               for value in pending]
                    record['exit']['effects_status'] = 'unmodeled'
                    record['exit']['completion'] = 'unconfirmed'
                    record['exit']['executions'][-1].update(status='unmodeled', issues=issues)
                    completed.extend([(kind, copy.deepcopy(state), copy.deepcopy(pending), exception),
                                      ('raise', copy.deepcopy(state), [], None)])
                    if kind in ('raise', 'unknown'):
                        completed.append(('normal', copy.deepcopy(state), [], None))
                    if call:
                        call.implicit_protocol.update(completion='unconfirmed',
                            exit_outcomes=_unique({'kind': item[0],
                                'exception': item[3] if item[0] == 'raise' else None}
                                for item in completed[first_outcome:]))
                    continue
                record['exit']['executions'][-1]['status'] = 'source_modeled'
                if all(item.get('status') == 'source_modeled' for item in record['exit']['executions']):
                    record['exit']['completion'] = 'source_modeled'
                    if record['exit']['effects_status'] != 'source_noop':
                        record['exit']['effects_status'] = 'source_modeled'
                for exit_kind, updated, values, payload in executed:
                    if exit_kind == 'raise':
                        self.add_boundary('context_exit_exception_path', node, updated,
                            call_id=call.id, exception=payload, completion='exceptional')
                        completed.append(('raise', updated, [], payload))
                        continue
                    if kind == 'raise':
                        truth = payload.get('truth') if exit_kind == 'return' and isinstance(payload, dict) else False
                        if truth is None:
                            self.add_boundary('context_exit_truth_unresolved', node, updated,
                                call_id=call.id, affected_scope='unknown')
                            self.unknown_context_effects(updated)
                            record['exit']['executions'][-1]['status'] = 'truth_unconfirmed'
                            record['exit'].update(effects_status='unmodeled', completion='unconfirmed')
                        if truth is not False:
                            completed.append(('normal', copy.deepcopy(updated), [], None))
                        if truth is not True:
                            completed.append(('raise', copy.deepcopy(updated), [], exception))
                        if truth is None:
                            completed.append(('raise', copy.deepcopy(updated), [], None))
                    else:
                        completed.append((kind, updated, pending, exception))
                call.implicit_protocol.update(completion=(
                    'source_modeled' if record['exit']['executions'][-1]['status'] == 'source_modeled'
                    else 'unconfirmed'),
                    exit_outcomes=_unique({'kind': item[0],
                        'exception': item[3] if item[0] == 'raise' else None}
                        for item in completed[first_outcome:]))
            outcomes = completed
            if (record.get('bounded_temporary_receiver_effects') is not None
                    and record['exit'].get('executions')
                    and all(item.get('status') == 'source_modeled'
                            for item in record['exit']['executions'])):
                record['exit']['completion'] = 'source_modeled'
            if len(outcomes) > _CONTEXT_EXIT_PATH_LIMIT:
                self.add_boundary('context_exit_path_budget', node, _merge_env([item[1] for item in outcomes]),
                                  affected_scope='unknown',
                                  path_limit=_CONTEXT_EXIT_PATH_LIMIT)
                outcomes = []
                for kind in _unique(item[0] for item in completed):
                    paths = [item for item in completed if item[0] == kind]
                    state = _merge_env([item[1] for item in paths])
                    self.unknown_context_effects(state)
                    payloads = _unique(item[3] for item in paths)
                    payload = payloads[0] if len(payloads) == 1 else (
                        {'truth': None} if self.context_execution and kind == 'return' else None)
                    pending = _unique(dict(value, value_incomplete=True, instance_candidates=[])
                        if any(value.get(key) for key in ('instance_type', 'instance_candidates',
                            'class_type', 'callable_type')) or value.get('kind') == 'callable' else value
                        for item in paths for value in item[2])
                    outcomes.append((kind, state, pending, payload))
        self.conditions = before
        return outcomes

    def context_enter_call(self, item, index, node, values, target, env, proof):
        temporary = '$with:%s:%s' % (_call_key(self.ref.file_path, node), index)
        env[temporary] = copy.deepcopy(values) if target else [dict(value, value_incomplete=True)
                                                               for value in values]
        implicit = ast.Call(func=ast.Attribute(value=ast.Name(id=temporary, ctx=ast.Load()),
                             attr='__enter__', ctx=ast.Load()), args=[], keywords=[])
        for child in ast.walk(implicit):
            ast.copy_location(child, item.context_expr)
        implicit._flow_implicit_suffix = ':with_enter:%s' % index
        implicit._flow_implicit_protocol = proof
        implicit._flow_protocol_target = target
        self.expression(implicit, env)
        env.pop(temporary, None)
        call = next((call for call in reversed(self.calls)
                     if call.id == _call_key(self.ref.file_path, implicit)), None)
        if call is not None:
            call.callee_name = ast.unparse(item.context_expr) + '.__enter__'
            for boundary in self.result.boundaries:
                if boundary.get('call_id') == call.id and 'callee_name' in boundary:
                    boundary['callee_name'] = call.callee_name
        return call

    def with_statement(self, node, env):
        before = copy.deepcopy(self.conditions)
        exceptions = []
        exits = []
        for index, item in enumerate(node.items):
            temporary_effect = (bounded_temporary_receiver_attributes(self, item.context_expr, env)
                                if item.optional_vars is None else None)
            if _may_raise(item.context_expr):
                failed = copy.deepcopy(env)
                if exits:
                    self.add_boundary('context_expression_exception_effects_unmodeled', item.context_expr,
                                      failed, affected_scope='unknown')
                    self.unknown_context_effects(failed)
                exceptions.extend(self.cleanup_context_exits(node,
                    [('raise', failed, [], None)], exits, 'context_expression'))
            before_expression = copy.deepcopy(env) if temporary_effect is not None else None
            values = self.marked(self.expression(item.context_expr, env), item.context_expr)
            if temporary_effect is not None:
                env.clear()
                env.update(before_expression)
            target, receiver, issues = self.context_protocol(values, '__enter__')
            exit_target, _, exit_issues = self.context_protocol(values, '__exit__')
            if temporary_effect is not None:
                receiver = FunctionRef(**temporary_effect['receiver_class'])
                issues, exit_issues = [], []
            if exit_target is not None and not self.context_signature_valid(exit_target, 3):
                exit_issues.append('binding_unconfirmed')
            assumptions = ['source_snapshot_bindings_hold', 'standard_type_special_method_lookup',
                           'no_external_monkeypatch_or_import_hook']
            proof = {'kind': 'context_manager_enter', 'method': '__enter__', 'lookup': 'type_mro',
                'with_id': _call_key(self.ref.file_path, node), 'item_index': index,
                'basis': 'source_snapshot', 'runtime_target_confirmed': False,
                'receiver_class': asdict(receiver) if receiver else None,
                'assumptions': assumptions, 'issues': issues,
                'context_expression': self.evidence(item.context_expr)}
            if target is not None:
                proof['definition'] = self.evidence_at(target[0], target[1])
                hierarchy = self.analyzer._class_mro(receiver.module, receiver.qualname)
                proof['source_hashes'] = {path: self.analyzer.hashes[path] for path in sorted(
                    {self.ref.file_path, target[0].file_path, receiver.file_path}
                    | {ref.file_path for ref, _ in hierarchy or ()})
                    if path in self.analyzer.hashes}
            missing_exit = receiver is not None and exit_issues == ['definition_unavailable']
            call = (None if temporary_effect is not None or missing_exit else
                    self.context_enter_call(item, index, node, values, target, env, proof))
            if temporary_effect is not None:
                fact = {'paths': [[]], 'completion': 'normal_possible', 'issues': [],
                        'effects_status': 'source_modeled'}
            elif target and call:
                fact = self.analyzer._context_enter_returns(target, receiver)
            else:
                fact = {'paths': [], 'completion': 'unknown',
                        'issues': ['context_enter_unresolved']}
            if temporary_effect is None and missing_exit:
                fact = {'paths': [], 'completion': 'no_normal_return',
                        'issues': ['context_exit_definition_unavailable'], 'exceptions': ['TypeError']}
            elif temporary_effect is None and target is not None and not self.context_signature_valid(target, 0):
                fact = {'paths': [], 'completion': 'no_normal_return',
                        'issues': ['context_enter_binding_unconfirmed'], 'exceptions': ['TypeError']}
                if call is not None:
                    call.binding_status = 'invalid'
                    call.binding_issues.append({'kind': 'implicit_receiver_binding', 'status': 'invalid'})
            elif temporary_effect is None and call is not None and call.binding_status != 'complete':
                fact = {'paths': [], 'completion': 'unknown', 'issues': ['context_enter_binding_unconfirmed']}
            elif temporary_effect is None and call is None:
                fact = {'paths': [], 'completion': 'unknown', 'issues': ['context_enter_budget']}
            prior_conditions = copy.deepcopy(self.conditions)
            condition = {'context_enter': call.id if call else proof['with_id'] + ':enter:%s' % index,
                         'completion': 'normal_return', 'basis': 'source_snapshot'}
            self.conditions = self.conditions + [condition]
            returned = []
            complete = (temporary_effect is not None
                        or bool(fact['paths']) and not fact['issues'])
            for path in fact['paths']:
                if temporary_effect is not None:
                    break
                known = []
                for value in path:
                    alias = (value.get('kind') == 'parameter'
                        and value.get('source') == fact.get('parameter')
                        and value.get('relation') == 'direct'
                        and not value.get('projection') and not value.get('output_path'))
                    inputs = values if alias else [value] if value.get('instance_type') else []
                    for actual in inputs:
                        if actual.get('value_incomplete') or actual.get('relation') != 'direct':
                            continue
                        evidence = _unique(actual.get('evidence', []) + value.get('evidence', [])
                                           + [self.evidence(item.context_expr)])
                        known.append(dict(actual, kind='call_result', source=call.id,
                            evidence=evidence, conditions=_unique(actual.get('conditions', [])
                                + value.get('conditions', []) + self.conditions),
                            context_manager_return={'enter_call_id': call.id,
                                'identity': 'receiver_alias' if alias else 'return_instance',
                                'object_source': (actual.get('context_manager_return', {}).get(
                                    'object_source', actual['source']) if alias else
                                    '$context_instance:%s:%s' % (call.id, actual['source'])),
                                'return_evidence': value.get('evidence', [])}))
                complete = complete and bool(known)
                returned.extend(known)
            record = {'with_id': proof['with_id'], 'item_index': index,
                'source_hashes': copy.deepcopy(proof.get('source_hashes', {})),
                'context_expression': proof['context_expression'], 'manager_sources': copy.deepcopy(values),
                'as_target': self.evidence(item.optional_vars) if item.optional_vars else None,
                'conditions': copy.deepcopy(self.conditions),
                'enter': {'call_id': call.id if call else None,
                    'target': asdict(target[0]) if target else None, 'issues': _unique(issues + fact['issues']),
                    'return_status': 'source_proven' if complete else 'unconfirmed',
                    'completion': fact['completion'], 'effects_status': fact.get('effects_status', 'unmodeled')},
                'exit': {'target': asdict(exit_target[0]) if exit_target else None,
                    'effects_status': ('source_modeled' if temporary_effect is not None else
                        'source_noop' if self.context_exit_noop(exit_target) else 'unmodeled'),
                    'issues': exit_issues, 'completion': 'deferred'},
                'basis': 'source_snapshot', 'runtime_target_confirmed': False, 'assumptions': assumptions}
            if temporary_effect is not None:
                record['bounded_temporary_receiver_effects'] = temporary_effect
            self.context_managers.append(record)
            self.conditions = prior_conditions
            failed = copy.deepcopy(env)
            if exits and fact.get('exceptions', [None]) and fact.get('effects_status') != 'source_modeled':
                self.add_boundary('context_enter_exception_effects_unmodeled', item.context_expr,
                                  failed, affected_scope='unknown', call_id=call.id if call else None)
                self.unknown_context_effects(failed)
            exceptions.extend(self.cleanup_context_exits(node,
                [('raise', copy.deepcopy(failed), [], exception) for exception in fact.get('exceptions', [None])],
                exits, 'context_enter'))
            self.conditions = prior_conditions + [condition]
            if fact['completion'] == 'no_normal_return':
                self.add_boundary('context_enter_no_normal_return', item.context_expr, env, values,
                                  call_id=call.id if call else None, conditions=copy.deepcopy(self.conditions))
                self.conditions = before
                return exceptions
            exits.append(record)
            if not complete:
                self.add_boundary('context_enter_return_unresolved', item.context_expr, env, values,
                    call_id=call.id if call else None, issues=record['enter']['issues'],
                    conditions=copy.deepcopy(self.conditions))
                returned = [{'kind': 'call_result', 'source': condition['context_enter'],
                    'relation': 'direct', 'evidence': [self.evidence(item.context_expr)],
                    'conditions': copy.deepcopy(self.conditions)}]
            for reason in record['enter']['issues']:
                if reason in ('context_enter_budget', 'context_enter_recursion'):
                    self.add_boundary(reason, item.context_expr, env, values,
                                      call_id=call.id if call else None)
            if temporary_effect is not None:
                self.apply_temporary_receiver_attributes(env, temporary_effect, entering=True)
            elif fact.get('effects_status') != 'source_modeled':
                self.add_boundary('context_enter_effects_unmodeled', item.context_expr, env,
                    [value for items in env.values() for value in items],
                    affected_scope='unknown', call_id=call.id if call else None)
                self.unknown_context_effects(env)
            if call is not None:
                call.result_sources = copy.deepcopy(returned) if complete else []
            if item.optional_vars is not None:
                self.assign_target(item.optional_vars, returned, env, item.optional_vars)
        outcomes = self.block(node.body, env)
        outcomes = self.cleanup_context_exits(node, outcomes, exits)
        self.conditions = before
        return exceptions + outcomes
