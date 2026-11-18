## @package pcresolve.flow.transfer.summary_statements
#  Transfer Python statements and control flow.
#
#
#  Processes assignments, guards, exception paths and summary execution.
#  处理赋值、守卫、异常路径以及摘要执行过程。



import ast
import copy
from dataclasses import asdict
from pcresolve.facts.effect_facts import contains_yield
from pcresolve.facts.import_facts import import_facts
from pcresolve.flow.model.results import FlowCall, FunctionRef
from pcresolve.flow.proofs.callables._fresh_member_checks import (
    fresh_checks as fresh_mapping_member_checks,
)
from pcresolve.flow.proofs.callables._function_factory import factory_wrapper
from pcresolve.flow.proofs.callables.dispatch.keyword_validation import (
    checks as keyword_validation_checks,
)
from pcresolve.flow.proofs.containers.container_predicates import (
    checks as container_predicate_checks,
)
from pcresolve.flow.proofs.containers.mapping_attribute_transfer import (
    transfers as mapping_attribute_transfers,
)
from pcresolve.flow.proofs.containers.mapping_key_access import (
    footprints as mapping_key_access_footprints,
)
from pcresolve.flow.proofs.containers.mapping_return_transfer import (
    transfers as mapping_return_transfers,
)
from pcresolve.flow.proofs.namespaces.metadata._metadata_observer import (
    observer_effects,
)
from pcresolve.flow.proofs.namespaces.metadata._metadata_queries import metadata_query
from pcresolve.flow.proofs.protocols._cached_imports import cached_import
from pcresolve.flow.proofs.protocols.capture_rejection_guard import (
    checks as capture_rejection_checks,
)
from pcresolve.flow.transfer._summary_support import (
    _attribute_write_roots,
    _call_key,
    _exception_class,
    _loop_env,
    _loop_signature,
    _may_raise,
    _unique,
)
from pcresolve.flow.transfer.environment import (
    merge_environments as _merge_env,
    merge_result_sources as _merge_result_sources,
)


class StatementsMixin:
    def statement(self, node, env):
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()
        ## Construct normal outcomes while retaining earlier exceptional paths.
        ## 构造正常结果，同时保留此前的异常路径。
        #
        #  @param e Current abstract environment.
        #  @return Outcome tuple list.
        def normal(e):
            return [('normal', e, [], None)]
        if self.context_execution:
            if isinstance(node, ast.Nonlocal):
                return normal(env)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef,
                                 ast.Import, ast.ImportFrom, ast.AugAssign)):
                self.add_boundary('context_exit_definition_or_write_unmodeled', node, env,
                                  affected_scope='unknown')
            if isinstance(node, ast.Delete) and len(node.targets) != 1:
                self.add_boundary('context_exit_multiple_delete_unmodeled', node, env,
                                  affected_scope='unknown')
            if (isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
                    and not all(isinstance(target, ast.Name) for target in (
                        node.targets if isinstance(node, ast.Assign) else [node.target]))):
                self.add_boundary('context_exit_assignment_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, (ast.For, ast.While)):
                self.add_boundary('context_exit_control_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, ast.Try) and any(handler.type is not None and not (
                    isinstance(handler.type, ast.Name) and _exception_class(handler.type.id) is not None
                    and self.analyzer._builtin_name_status(self.ref, self.node, handler.type.id, env)
                        == 'confirmed_builtin') for handler in node.handlers):
                self.add_boundary('context_exit_handler_unmodeled', node, env, affected_scope='unknown')
            if isinstance(node, ast.If):
                truth = self.context_truth(node.test, env)
                if truth is not None:
                    before = self.conditions
                    self.conditions = before + [{'test': self.evidence(node.test), 'branch': truth}]
                    outcomes = self.block(node.body if truth else node.orelse, env)
                    self.conditions = before
                    return outcomes
                self.add_boundary('context_exit_guard_unresolved', node.test, env, affected_scope='unknown')
            if isinstance(node, ast.Return):
                truth = self.context_truth(node.value, env) if node.value is not None else False
                previous = copy.deepcopy(env)
                values = self.marked(self.expression(node.value, env), node)
                exceptional, possible = self.context_operation_exits(node.value, previous, env)
                return exceptional + ([('return', env, values, {'truth': truth})] if possible else [])
        previous = copy.deepcopy(env) if self.context_execution else None
        exceptional = []
        # A possible exception uses the environment BEFORE evaluation. Simple
        # name/constant assignments cannot import a later definition into it.
        # 可能异常沿用求值前的环境，不能引入之后才建立的绑定。
        expressions = []
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Return, ast.Expr)):
            expressions = [node.value]
        elif isinstance(node, ast.If):
            expressions = [node.test]
        if any(_may_raise(e) for e in expressions if e is not None):
            exceptional = [('raise', copy.deepcopy(env), [], None)]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            positional = node.args.posonlyargs + node.args.args
            defaults = list(zip(positional[len(positional) - len(node.args.defaults):], node.args.defaults))
            defaults += [(a, d) for a, d in zip(node.args.kwonlyargs, node.args.kw_defaults) if d is not None]
            values = {a.arg: self.expression(d, env) for a, d in defaults}
            target = FunctionRef(self.ref.module, self.ref.qualname + '.' + node.name,
                                 self.ref.file_path, node.lineno)
            env[node.name] = [self.callable_value(target, node, values)]
            return normal(env)
        if isinstance(node, ast.ClassDef):
            env[node.name] = [{
                'kind': 'class',
                'module': self.ref.module,
                'source': self.ref.qualname + '.' + node.name,
                'relation': 'direct',
                'evidence': [self.evidence(node)],
                'conditions': list(self.conditions)}]
            return normal(env)
        if isinstance(node, ast.If):
            self.expression(node.test, env)
            before = list(self.conditions)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
            positive = copy.deepcopy(env)
            left = self.block(node.body, positive) if self.refine_guard(node.test, positive) else []
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
            negative = copy.deepcopy(env)
            right = (self.block(node.orelse, negative)
                     if self.refine_guard(node.test, negative, positive=False) else [])
            self.conditions = before
            if getattr(self.analyzer, '_conditional_source_state', False):
                normal_left = any(outcome[0] == 'normal' for outcome in left)
                normal_right = any(outcome[0] == 'normal' for outcome in right)
                if normal_left != normal_right:
                    predicate = {'test': self.evidence(node.test), 'branch': normal_left}
                    for kind, state, _, _ in left + right:
                        if kind == 'normal':
                            for name, values in state.items():
                                state[name] = [dict(value, conditions=_unique(
                                    value.get('conditions', []) + [predicate])) for value in values]
            return exceptional + left + right
        if isinstance(node, ast.Try):
            return self.try_statement(node, env)
        if isinstance(node, ast.With):
            return self.with_statement(node, env)
        if isinstance(node, ast.AsyncWith):
            self.add_boundary('async_with_unsupported', node, env, affected_scope='unknown')
            return [('unknown', env, [], None)]
        if isinstance(node, (ast.For, ast.While)):
            before = copy.deepcopy(env)
            head = copy.deepcopy(env)
            exits = []
            if isinstance(node, ast.For):
                iterable = self.marked(self.project(self.expression(node.iter, env), '*', env), node.iter, 'derived')
            converged = False
            for iteration in range(16):
                body_env = copy.deepcopy(head)
                if isinstance(node, ast.For):
                    self.assign_target(node.target, iterable, body_env, node)
                else:
                    self.expression(node.test, body_env)
                outcomes = self.block(node.body, body_env)
                exits.extend(o for o in outcomes if o[0] not in ('normal', 'continue'))
                continuing = [before] + [e for k, e, _, _ in outcomes if k in ('normal', 'continue')]
                updated = _loop_env(_merge_env(continuing))
                if _loop_signature(updated) == _loop_signature(head):
                    head = updated
                    converged = True
                    break
                head = updated
            else:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'loop_iteration_limit',
                                               'evidence': self.evidence(node)})
            self.loops.append({'lineno': node.lineno, 'col_offset': node.col_offset,
                               'iterations': iteration + 1,
                               'status': 'converged' if converged else 'bounded',
                               'semantics': 'may-flow; one witness per dependency'})
            completed = self.block(node.orelse, head)
            completed += [('normal', e, [], None) for k, e, _, _ in exits if k == 'break']
            completed += [o for o in exits if o[0] != 'break']
            return completed
        if isinstance(node, (ast.Break, ast.Continue)):
            return [('break' if isinstance(node, ast.Break) else 'continue', env, [], None)]
        if isinstance(node, ast.Delete):
            for target in node.targets:
                self.invalidate_class_origins([value for name in _attribute_write_roots(target)
                    for value in env.get(name, [])], env)
                if isinstance(target, ast.Name):
                    values = env.get(target.id, [])
                    self.add_boundary('unsupported_assignment', node, env, values)
                    env[target.id] = []
                    continue
                if isinstance(target, ast.Subscript):
                    receivers = self.container_values(self.expression(target.value, env))
                    self.expression(target.slice, env)
                    if (receivers and all(value.get('kind') == 'container'
                            and value.get('container_shape') == 'dict'
                            for value in receivers)):
                        try:
                            key = ast.literal_eval(target.slice)
                        except (ValueError, TypeError):
                            key = '*'
                        roots, unknown = self.affected_values(receivers, env)
                        if key != '*' and len({value['source']
                                               for value in receivers}) == 1:
                            for reference in receivers:
                                remaining = []
                                for value in env.get(reference['source'], []):
                                    path = value.get('output_path', [])
                                    if path and path[0] == key:
                                        continue
                                    if path and path[0] == '*':
                                        value = dict(value, excluded_paths=_unique(
                                            value.get('excluded_paths', []) + [[key]]),
                                            conditions=value.get('conditions', []) +
                                                       list(self.conditions))
                                    remaining.append(value)
                                env[reference['source']] = remaining
                        self.mapping_effects.append({
                            'operation': 'delete', 'mapping': roots,
                            'element_path': [key],
                            'state_after': ('conditional' if self.conditions
                                            else 'absent' if key != '*' else 'unknown'),
                            'status': 'unknown_key' if key == '*' or unknown else 'bounded',
                            'conditions': list(self.conditions),
                            'evidence': self.evidence(node)})
                        if self.context_execution:
                            if key == '*':
                                self.add_boundary('context_exit_data_protocol_unmodeled', node, env,
                                                  affected_scope='unknown')
                            exceptional, possible = self.context_operation_exits(target, previous, env)
                            if not possible:
                                return exceptional
                        continue
                values = []
                if isinstance(target, (ast.Attribute, ast.Subscript)):
                    values = self.expression(target.value, env)
                self.add_boundary('unsupported_assignment', node, env, values)
            return exceptional + normal(env)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            if (isinstance(node, ast.Assign) and len(node.targets) == 1
                    and isinstance(node.targets[0], (ast.Tuple, ast.List))
                    and isinstance(node.value, (ast.Tuple, ast.List))
                    and len(node.targets[0].elts) == len(node.value.elts)
                    and not any(isinstance(n, ast.Starred) for n in node.targets[0].elts + node.value.elts)):
                elements = [self.expression(v, env) for v in node.value.elts]
                for target, values in zip(node.targets[0].elts, elements):
                    self.assign_target(target, values, env, node)
                return exceptional + normal(env)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            values = self.expression(node.value, env)
            if self.context_execution:
                exceptional, possible = self.context_operation_exits(node.value, previous, env, exceptional)
                if not possible:
                    return exceptional
                literal = self.literal_fact(node.value, env)
                if literal is not None:
                    values = [dict(value, literal=literal) for value in values] or [
                        {'kind': 'context_data', 'source': self.ref.qualname,
                         'literal': literal, 'relation': 'direct',
                         'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}]
            if isinstance(node, ast.AugAssign):
                values = self.marked(self.expression(node.target, env) + values, node, 'derived')
            for target in targets:
                self.assign_target(target, values, env, node)
            return exceptional + normal(env)
        if isinstance(node, ast.Return):
            return exceptional + [('return', env, self.marked(self.expression(node.value, env), node), None)]
        if isinstance(node, ast.Expr):
            self.expression(node.value, env)
            if self.context_execution and isinstance(node.value, ast.Call):
                exceptional, possible = self.context_operation_exits(node.value, previous, env, exceptional)
                if not possible:
                    return exceptional
            return exceptional + normal(env)
        if isinstance(node, ast.Raise):
            self.expression(node.exc, env)
            expression = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            exception = expression.id if isinstance(expression, ast.Name) else None
            return [('raise', env, [], exception)]
        if isinstance(node, ast.Import):
            for fact in import_facts(node):
                env[fact.python_binding] = [{
                    'kind': 'import',
                    'source': fact.name if fact.asname else fact.python_binding,
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)}]
            return normal(env)
        if isinstance(node, ast.ImportFrom):
            cached = cached_import(self.analyzer, self.ref, node, self.evidence, self.conditions)
            if cached is not None and cached not in self.cached_local_imports:
                self.cached_local_imports.append(cached)
            if node.level:
                self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'relative_local_import', 'evidence': self.evidence(node)})
            for fact in import_facts(node):
                env[fact.python_binding] = ([{'kind': 'import',
                    'source': fact.module + '.' + fact.name,
                    'relation': 'direct', 'evidence': [self.evidence(node)],
                    'conditions': list(self.conditions)}]
                                                  if not node.level else [])
            return normal(env)
        if isinstance(node, ast.Pass):
            return normal(env)
        self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_statement', 'evidence': self.evidence(node)})
        return [('unknown', env, [], None)]

    def assign_target(self, target, values, env, node):
        attribute = self.attribute_key(target, env)
        self.invalidate_class_origins([value for name in _attribute_write_roots(target)
            for value in env.get(name, [])], env)
        if attribute is not None:
            known = self.class_values(values, allow_incomplete=True, env=env)
            env[attribute[0]] = [dict(value, attribute_provenance=[{
                'receiver_class': attribute[1], 'attribute': target.attr,
                'storage_attribute': attribute[0].rsplit(':', 1)[-1],
                'assignment': self.evidence(node), 'conditions': copy.deepcopy(self.conditions)}])
                for value in self.marked(known, node)]
            if not known:
                self.add_boundary('unsupported_assignment', node, env, values)
            return
        if isinstance(target, ast.Attribute):
            candidates, _ = self.callable_targets(self.expression(target.value, env))
            self.modified_return_callables.update(
                (candidate[0].module, candidate[0].qualname) for candidate in candidates)
        for name in _attribute_write_roots(target):
            root = target
            while isinstance(root, (ast.Attribute, ast.Subscript)):
                root = root.value
            if isinstance(root, ast.Name):
                self.invalidate_literals(self.expression(root, env), env)
                candidates, _ = self.callable_targets(self.expression(root, env))
                self.modified_return_callables.update(
                    (candidate[0].module, candidate[0].qualname) for candidate in candidates)
            imported = env.get(name, [])
            modified = {value['source'] for value in imported
                        if value.get('instance_type') or value.get('class_type') or value.get('instance_candidates')}
            if modified:
                for key, sources in env.items():
                    env[key] = [dict(value, value_incomplete=True, instance_candidates=[])
                                if value.get('source') in modified and (
                                    value.get('instance_type') or value.get('class_type') or value.get('instance_candidates'))
                                else value for value in sources]
            if not imported and name not in env:
                source = self.analyzer.imports.get(self.ref.module, {}).get(name)
                if source:
                    imported = [{'kind': 'import', 'source': source,
                                 'relation': 'direct',
                                 'evidence': [self.evidence(node)],
                                 'conditions': list(self.conditions)}]
            if imported and all(value.get('kind') == 'import' for value in imported):
                env[name] = [dict(value, import_modified=True) for value in imported]
        if isinstance(target, ast.Name):
            env[target.id] = self.marked(values, node)
        elif isinstance(target, (ast.Tuple, ast.List)) and not any(isinstance(t, ast.Starred) for t in target.elts):
            for index, element in enumerate(target.elts):
                projected = self.project(values, index, env)
                self.assign_target(element, projected, env, node)
        elif isinstance(target, ast.Subscript):
            receiver = self.container_values(self.expression(target.value, env))
            if receiver and all(v['kind'] == 'container' and v['container_shape'] == 'dict' for v in receiver):
                index = target.slice.value if isinstance(target.slice, ast.Constant) else '*'
                self.expression(target.slice, env)
                for ref in receiver:
                    previous = env.get(ref['source'], [])
                    if index != '*' and len({v['source'] for v in receiver}) == 1:
                        updated = []
                        for value in previous:
                            path = value.get('output_path', [None])
                            if path[0] == index:
                                continue
                            if path[0] == '*':
                                value = dict(value, excluded_paths=_unique(
                                    value.get('excluded_paths', []) + [[index]]))
                            updated.append(value)
                        previous = updated
                    inserted = [dict(v, output_path=[index] + v.get('output_path', []))
                                for v in self.marked(self.materialize(values, env), node)]
                    env[ref['source']] = _loop_env({'items': previous + inserted})['items']
                    keys = env.get(ref['source'] + '$keys', [])
                    for marker in keys:
                        if marker['key'] == '*' and index != '*':
                            marker.setdefault('excluded_keys', []).append(index)
                    env[ref['source'] + '$keys'] = _unique(keys +
                        [{'kind': 'key', 'source': repr(index), 'key': index}])
            else:
                target_values = (env.get(target.value.id, [])
                                 if isinstance(target.value, ast.Name) else [])
                try:
                    affected_key = ast.literal_eval(target.slice)
                except (ValueError, TypeError):
                    affected_key = '*'
                target_values = [dict(value, output_path=[affected_key] +
                                      value.get('output_path', []))
                                 for value in target_values]
                self.add_boundary('unsupported_assignment', node, env,
                                  list(values) + list(target_values))
        else:
            target_values = (env.get(target.value.id, [])
                             if isinstance(target, ast.Attribute)
                             and isinstance(target.value, ast.Name) else [])
            self.add_boundary('unsupported_assignment', node, env,
                              list(values) + list(target_values))

    def guard_callable(self, node, env):
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value
        if not isinstance(root, ast.Name):
            return None
        if isinstance(node, ast.Attribute):
            bindings = env.get(root.id)
            if bindings is not None:
                if not bindings or any(value.get('kind') != 'import' for value in bindings):
                    return None
            elif root.id not in self.analyzer.imports.get(self.ref.module, {}):
                return None
        candidates, complete = self.callable_targets(self.expression(node, env))
        if not complete or len(candidates) != 1:
            return None
        ref, function = candidates[0]
        if ('.' in ref.qualname or not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
                or function.decorator_list):
            return None
        return candidates[0]

    def refine_guard(self, test, env, positive=True, allow_callable=True):
        if (getattr(self.analyzer, '_conditional_source_state', False)
                and isinstance(test, ast.Constant) and bool(test.value) != positive):
            return False
        if (getattr(self.analyzer, '_conditional_source_state', False) and allow_callable
                and isinstance(test, ast.Compare) and len(test.ops) == len(test.comparators) == 1
                and isinstance(test.ops[0], (ast.Is, ast.IsNot))
                and isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Name)):
            sides = [self.class_values(env.get(value.id, []), env=env)
                     for value in (test.left, test.comparators[0])]
            if all(values and not any(value.get('value_incomplete') for value in values)
                   and len(_unique([value['class_type'] for value in values])) == 1 for values in sides):
                identical = sides[0][0]['class_type'] == sides[1][0]['class_type']
                truth = identical if isinstance(test.ops[0], ast.Is) else not identical
                if truth != positive:
                    return False
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return self.refine_guard(test.operand, env, not positive, allow_callable)
        if isinstance(test, ast.BoolOp) and (positive and isinstance(test.op, ast.And)
                or not positive and isinstance(test.op, ast.Or)):
            # Short-circuit evaluation already refines each operand before the
            # next one runs. Do not replay identities after intervening effects.
            allow_callable = allow_callable and not any(isinstance(node, (
                ast.Call, ast.NamedExpr, ast.Await, ast.Yield, ast.YieldFrom,
                ast.Subscript, ast.BinOp)) or isinstance(node, ast.Compare)
                and not all(isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops)
                for node in ast.walk(test))
            for operand in test.values:
                if not self.refine_guard(operand, env, positive, allow_callable):
                    return False
        if (allow_callable and isinstance(test, ast.Compare) and len(test.ops) == len(test.comparators) == 1
                and isinstance(test.ops[0], (ast.Is, ast.IsNot))):
            equal = positive != isinstance(test.ops[0], ast.IsNot)
            for variable, source in ((test.left, test.comparators[0]),
                                     (test.comparators[0], test.left)):
                if not isinstance(variable, ast.Name) or not env.get(variable.id):
                    continue
                values = env[variable.id]
                if any(value.get('kind') not in ('parameter', 'capture', 'callable')
                       or value.get('relation') != 'direct' or any(value.get(flag) for flag in (
                           'projection', 'output_path', 'value_incomplete')) for value in values):
                    continue
                target = self.guard_callable(source, env)
                if target is None:
                    continue
                if all(value.get('literal') is not None for value in values):
                    return not equal
                candidates, complete = self.callable_targets(values)
                if complete and (all(candidate[0] != target[0] for candidate in candidates) if equal
                        else all(candidate[0] == target[0] for candidate in candidates)):
                    return False
                remaining = []
                for value in values:
                    known, closed = self.callable_targets([value])
                    if closed and len(known) == 1 and (known[0][0] == target[0]) != equal:
                        continue
                    remaining.append(value)
                if not equal:
                    env[variable.id] = remaining
                    return bool(remaining)
                evidence = self.evidence(test)
                env[variable.id] = [dict(value, callable_type=asdict(target[0]),
                    callable_evidence=_unique(value.get('callable_evidence', []) + [evidence]),
                    conditions=_unique(value.get('conditions', []) + list(self.conditions)))
                    for value in remaining]
                return True
        if (allow_callable and isinstance(test, ast.Call) and isinstance(test.func, ast.Name)
                and test.func.id == 'isinstance' and len(test.args) == 2 and not test.keywords
                and isinstance(test.args[0], ast.Name) and isinstance(test.args[1], ast.Name)
                and test.args[1].id == 'str'
                and all(name not in env and name not in self.analyzer.imports.get(self.ref.module, {})
                        and name not in self.analyzer.module_bindings.get(self.ref.module, set())
                        and self.analyzer._resolve(self.ref, name) is None for name in ('str', 'isinstance'))):
            name = test.args[0].id
            targets, complete = self.callable_targets(env.get(name, []))
            if targets and complete:
                # Closed source function objects are not strings. Do not run
                # an impossible recursive branch and contaminate its sibling.
                return not positive
            if positive:
                env[name] = [dict(v, python_shape='str',
                                  conditions=v.get('conditions', []) + list(self.conditions))
                             for v in env.get(name, [])]
        return True

    def try_statement(self, node, env):
        outcomes = self.block(node.body, copy.deepcopy(env))
        completed = []
        # Merge exception prefixes by known exception spelling. This bounds
        # repeated handler analysis and preserves definitions at raise sites.
        raised = {}
        for kind, state, values, exception in outcomes:
            if kind == 'normal':
                completed.extend(self.block(node.orelse, state))
            elif kind == 'raise':
                raised.setdefault(exception, []).append(state)
            else:
                completed.append((kind, state, values, exception))
        for exception, states in raised.items():
            state = _merge_env(states)
            caught = False
            for handler in node.handlers:
                names = ([n.id for n in handler.type.elts if isinstance(n, ast.Name)]
                         if isinstance(handler.type, ast.Tuple)
                         else [handler.type.id] if isinstance(handler.type, ast.Name) else [])
                exact = handler.type is None
                raised_class = _exception_class(exception)
                handler_classes = [_exception_class(n) for n in names]
                # Unknown/custom inheritance cannot safely exclude a handler.
                if raised_class and handler_classes and all(handler_classes):
                    if not any(issubclass(raised_class, cls) for cls in handler_classes):
                        continue
                    exact = True
                before = list(self.conditions)
                self.conditions = before + [{'handler': self.evidence(handler), 'exception': exception or 'unknown'}]
                handled = copy.deepcopy(state)
                if handler.name:
                    handled[handler.name] = []
                handler_exits = self.block(handler.body, handled)
                for item in handler_exits:
                    if handler.name:
                        item[1].pop(handler.name, None)
                completed.extend(handler_exits)
                self.conditions = before
                if exact:
                    caught = True
                    break
            if not caught:
                completed.append(('raise', state, [], exception))
        if not node.finalbody:
            return completed
        finalized = []
        for kind, state, values, exception in completed:
            for final_kind, final_env, final_values, final_exc in self.block(node.finalbody, copy.deepcopy(state)):
                if final_kind == 'normal':
                    finalized.append((kind, final_env, values, exception))
                else:
                    finalized.append((final_kind, final_env, final_values, final_exc))
        return finalized

    def run(self):
        if getattr(self.node, '_flow_branch_budget', None) is not None:
            self.result.boundaries.append({'function': asdict(self.ref),
                'reason': 'literal_branch_budget',
                'evidence': self.evidence(self.node._flow_branch_budget)})
        args = self.node.args
        parameters = args.posonlyargs + args.args + args.kwonlyargs
        parameters += [a for a in (args.vararg, args.kwarg) if a]
        env = {a.arg: [{'kind': 'parameter', 'source': a.arg, 'relation': 'direct',
                        'evidence': [self.evidence(a)], 'conditions': []}] for a in parameters}
        for parameter, facts in self.incoming.items():
            if parameter in env:
                root = env[parameter][0]
                env[parameter] = [dict(root, **fact) for fact in facts]
        if self.receiver_class is not None and parameters:
            env[parameters[0].arg][0]['class_type'] = asdict(self.receiver_class)
        for values in list(env.values()):
            for value in values:
                for effect in value.get('class_lookup_mutations', []):
                    self.register_class_lookup_effect(effect, env)
        for parameter, shape in ((args.vararg, 'tuple'), (args.kwarg, 'dict')):
            if parameter is None:
                continue
            heap = '$parameter:%s:%s:%s' % (
                self.ref.file_path, self.ref.qualname, parameter.arg)
            root = env[parameter.arg][0]
            env[heap] = [dict(root, relation='contained', output_path=['*'])]
            env[heap + '$keys'] = [
                {'kind': 'key', 'source': '*', 'key': '*'}]
            env[parameter.arg] = [{
                'kind': 'container', 'source': heap,
                'container_shape': shape, 'parameter_container': parameter.arg,
                'relation': 'direct', 'evidence': [self.evidence(parameter)],
                'conditions': []}]
        shape_contract = self.analyzer.parameter_shapes.get(
            self.ref.module + '.' + self.ref.qualname, {})
        shapes = shape_contract.get('parameters', {})
        for name, shape in shapes.items():
            if name in env:
                env[name] = [dict(value, python_shape=shape,
                                  shape_provenance=shape_contract['provenance'])
                             for value in env[name]]
        for local in self.analyzer._scope_facts(self.node).bound:
            env.setdefault(local, [])
        capture_objects = {}
        for capture in self.analyzer._captures(self.ref, self.node):
            root = {'kind': 'capture', 'source': capture, 'relation': 'direct',
                    'evidence': [], 'conditions': []}
            facts = self.incoming.get(capture, [])
            binding = facts[0].get('capture_container_binding') if len(facts) == 1 else None
            if binding:
                identity = binding['source'], binding['shape']
                if identity not in capture_objects:
                    heap = '$capture:%s:%s:%s' % (self.ref.file_path, self.ref.qualname, capture)
                    capture_objects[identity] = heap, capture
                    env[heap] = [dict(root, relation='contained', output_path=['*'])]
                    env[heap + '$keys'] = [{'kind': 'key', 'source': '*', 'key': '*'}]
                heap, origin = capture_objects[identity]
                env[capture] = [{'kind': 'container', 'source': heap,
                    'container_shape': binding['shape'], 'parameter_container': origin,
                    'relation': 'direct', 'evidence': copy.deepcopy(binding.get('evidence', [])),
                    'conditions': copy.deepcopy(binding.get('conditions', []))}]
            else:
                env[capture] = [root]
        outcomes = ([('return', env,
                      self.marked(self.expression(self.node.body, env), self.node.body), None)]
                    if isinstance(self.node, ast.Lambda) else self.block(self.node.body, env))
        generator = contains_yield(self.node)
        self.outcomes = outcomes
        self.exit_kinds = {kind for kind, _, _, _ in outcomes}
        for kind, state, values, _ in outcomes:
            if kind == 'return' and not generator:
                returned = self.materialize(values, state)
                self.normal_returns.append(returned)
                self.returns.extend(returned)
            elif kind in ('normal', 'unknown'):
                self.incomplete_return = True
        if generator:
            self.returns.extend(self.yields)
        self.returns = _unique(self.returns)
        merged = {}
        for call in self.calls:
            if call.id not in merged:
                merged[call.id] = call
            else:
                previous = merged[call.id]
                if previous.target != call.target:
                    previous.target = None
                if (previous.target_status != call.target_status
                        and 'local_container_protocol' in (
                            previous.target_status, call.target_status)):
                    previous.target = None
                    previous.target_status = 'receiver_unresolved'
                for attribute in ('parameter_bindings', 'parameter_flows', 'argument_sources', 'argument_flows',
                                   'capture_bindings', 'receiver_sources',
                                   'receiver_type_evidence', 'mutation_flows',
                                   'decorator_identity_evidence',
                                   'return_dependencies', 'effects', 'target_candidates',
                                   'binding_issues'):
                    setattr(previous, attribute, _unique(getattr(previous, attribute) + getattr(call, attribute)))
                previous.callable_sources = _unique(previous.callable_sources + call.callable_sources)
                previous.conditional_returns = _unique(previous.conditional_returns + call.conditional_returns)
                previous.class_method_bindings = _unique(previous.class_method_bindings + call.class_method_bindings)
                previous.class_metadata_bindings = _unique(previous.class_metadata_bindings + call.class_metadata_bindings)
                previous.class_read_bindings = _unique(previous.class_read_bindings + call.class_read_bindings)
                previous.conditional_source_bindings = _unique(
                    previous.conditional_source_bindings + call.conditional_source_bindings)
                previous.candidate_paths = _unique(previous.candidate_paths + call.candidate_paths)
                previous.constructor_bindings = _unique(previous.constructor_bindings + call.constructor_bindings)
                previous.instance_method_bindings = _unique(previous.instance_method_bindings + call.instance_method_bindings)
                previous.result_sources = _merge_result_sources(
                    previous.result_sources, call.result_sources)
                if previous.binding_status != call.binding_status:
                    previous.binding_status = 'uncertain'
        self.calls = list(merged.values())
        partial_effect_calls = {boundary.get('call_id') for boundary in self.result.boundaries
                                if boundary['reason'] == 'mapping_effect_unproven'}
        for call in self.calls:
            if call.id in partial_effect_calls:
                for effect in call.effects:
                    if effect.get('completion') == 'normal_return':
                        effect.update(state_after='conditional', status='partial_context')
        for effect in self.mapping_effects:
            if effect.get('call_id') in partial_effect_calls:
                effect.update(state_after='conditional', status='partial_context')
        ## Collect source nodes for the function summary.
        ## 收集函数摘要使用的源码节点。
        #
        #  @param node AST node to inspect.
        #  @return None
        def collect(node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                return
            if isinstance(node, ast.Call):
                call_id = _call_key(self.ref.file_path, node)
                if call_id not in merged and self.remaining > 0:
                    self.remaining -= 1
                    call = FlowCall(call_id, self.ref, ast.unparse(node.func), node.lineno, node.col_offset,
                                    node.end_lineno, node.end_col_offset,
                                    analysis_status='not_analyzed', target_status='flow_not_analyzed')
                    self.calls.append(call)
                    merged[call_id] = call
            for child in ast.iter_child_nodes(node):
                collect(child)
        body = [self.node.body] if isinstance(self.node, ast.Lambda) else self.node.body
        for statement in body:
            collect(statement)
        self.calls.sort(key=lambda c: (c.lineno, c.col_offset))
        for call in self.calls:
            call.return_flows = [dict(v, status='flow_found') for v in self.returns
                                 if v['kind'] == 'call_result' and v['source'] == call.id]
        self.result.functions.append({'function': asdict(self.ref),
                                      'parameters': [a.arg for a in parameters],
                                      'fresh_mapping_member_checks': fresh_mapping_member_checks(self),
                                      'keyword_checks': keyword_validation_checks(
                                          self.analyzer, self.ref, self.node),
                                      'capture_rejection_guards': capture_rejection_checks(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_key_accesses': mapping_key_access_footprints(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_attribute_transfers': mapping_attribute_transfers(
                                          self.analyzer, self.ref, self.node),
                                      'mapping_return_transfers': mapping_return_transfers(
                                          self.analyzer, self.ref, self.node),
                                      'container_predicates': container_predicate_checks(
                                          self.analyzer, self.ref, self.node),
                                      'parameter_shapes': copy.deepcopy(shapes),
                                      'generator': generator,
                                      'loops': self.loops,
                                      'mapping_effects': self.mapping_effects,
                                      'returns': self.returns,
                                      'decorator_effects': self.analyzer._decoration_facts((self.ref, self.node))})
        if self.context_managers:
            self.result.functions[-1]['context_managers'] = self.context_managers
        fresh = self.analyzer._fresh_decoration_facts((self.ref, self.node))
        if fresh:
            self.result.functions[-1]['fresh_function_decorations'] = fresh
        wrapper = factory_wrapper(self.analyzer, (self.ref, self.node))
        if wrapper is not None and 'forwarding' in wrapper:
            self.result.functions[-1]['source_wrapper_forwarding'] = [wrapper]
        query = metadata_query(self.analyzer, (self.ref, self.node))
        if query is not None:
            self.result.functions[-1]['native_callable_metadata_queries'] = [query]
        observers = observer_effects(self.analyzer, (self.ref, self.node))
        if observers:
            self.result.functions[-1]['native_class_metadata_observers'] = observers
        if self.cached_local_imports:
            self.result.functions[-1]['cached_local_imports'] = self.cached_local_imports
        decorations = self.result.functions[-1]['decorator_effects']
        if decorations and self.analyzer._descriptor_kind((self.ref, self.node)) is None:
            for fact in decorations:
                if fact['body_binding_status'] != 'preserved':
                    self.result.boundaries.append({'function': asdict(self.ref),
                        'reason': 'decorator_effect_unconfirmed',
                        'identity_status': fact['identity_status'],
                        'body_binding_status': fact['body_binding_status'],
                        'issues': copy.deepcopy(fact['boundaries']),
                        'evidence': copy.deepcopy(fact['expression'])})
        object_fact, _ = self.analyzer._object_returns((self.ref, self.node))
        if object_fact:
            self.result.functions[-1]['return_objects'] = [{
                'parameter': object_fact['parameter'], 'identity': 'argument_alias',
                'evidence': [self.evidence(statement)
                             for statement in object_fact['evidence']]}]
            if object_fact.get('conditions'):
                self.result.functions[-1]['return_objects'][0]['conditions'] = object_fact['conditions']
            if object_fact.get('effects'):
                self.result.functions[-1]['return_objects'][0].update(
                    completion='normal_return', requires_shapes=_unique([
                        {'parameter': effect.target,
                         'shapes': ['dict'] if effect.receiver_shape else ['dict', 'list', 'set']}
                        for effect in object_fact['effects']]))
        guarded = self.analyzer._guarded_object_returns((self.ref, self.node))
        if guarded:
            self.result.functions[-1]['return_objects'] = _unique(
                self.result.functions[-1].get('return_objects', []) + guarded)
        if self.receiver_class is not None:
            self.result.functions[-1]['receiver_contexts'] = [asdict(self.receiver_class)]
        self.result.calls.extend(self.calls)
