## @package pcresolve.flow.transfer.summary_expressions
#  Transfer Python expressions into flow facts.
#
#
#  Dispatches expression forms and preflight checks within one query-local summary.
#  在单次查询摘要中分派表达式处理和前置边界检查。



import ast
import copy
from dataclasses import asdict
from pcresolve.flow.model.results import FunctionRef
from pcresolve.flow.transfer._summary_support import _unique
from pcresolve.flow.transfer.environment import merge_environments as _merge_env


## Dispatch expression syntax into dependency alternatives.
## 将表达式语法分派为依赖候选。
class ExpressionsMixin:
    ## Evaluate an expression into dependencies under one environment.
    ## 在给定环境下将表达式求值为依赖候选。
    #
    #  @param node Expression syntax being evaluated; None yields no dependencies.
    #  @param env Abstract environment used for name and attribute lookups.
    #  @return Dependency alternatives, or an empty list when unresolved.
    def expression(self, node, env):
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()
        if node is None:
            return []
        self._expression_preflight(node, env)
        result = self._expression_part_01(node, env)
        if result is not None:
            return result
        result = self._expression_part_02(node, env)
        if result is not None:
            return result
        result = self._expression_part_03(node, env)
        if result is not None:
            return result
        result = self._expression_part_04(node, env)
        if result is not None:
            return result
        result = self._expression_part_05(node, env)
        if result is not None:
            return result
        result = self._expression_part_06(node, env)
        if result is not None:
            return result
        result = self._expression_part_07(node, env)
        if result is not None:
            return result
        result = self._expression_part_08(node, env)
        if result is not None:
            return result
        result = self._expression_part_09(node, env)
        if result is not None:
            return result
        result = self._expression_part_10(node, env)
        if result is not None:
            return result
        result = self._expression_part_11(node, env)
        if result is not None:
            return result
        result = self._expression_part_12(node, env)
        if result is not None:
            return result
        result = self._expression_part_13(node, env)
        if result is not None:
            return result
        values = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.expr):
                values.extend(self.materialize(self.expression(child, env), env))
        relation = 'contained' if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)) else 'derived'
        return self.marked(values, node, relation)

    ## Mark expression forms that cross the context-exit safety boundary.
    ## 标记触及上下文退出安全边界的表达式。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return None.
    def _expression_preflight(self, node, env):
        if self.analyzer._analysis_budget is not None:
            self.analyzer._analysis_budget.checkpoint()
        if (self.context_execution and isinstance(node, (ast.Tuple, ast.List, ast.Dict))
                and any(isinstance(child, ast.Call) for child in ast.walk(node))):
            self.add_boundary('context_exit_nested_expression_unmodeled', node, env,
                              affected_scope='unknown')
        if self.context_execution and (isinstance(node, (ast.Attribute, ast.Subscript,
                ast.BinOp, ast.BoolOp, ast.IfExp, ast.NamedExpr, ast.Lambda,
                ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp))
                or isinstance(node, ast.Compare) and not all(
                    isinstance(op, (ast.Is, ast.IsNot)) for op in node.ops)
                or isinstance(node, ast.UnaryOp) and self.context_truth(node, env) is None):
            self.add_boundary('context_exit_data_protocol_unmodeled', node, env,
                              affected_scope='unknown')
        if self.context_execution and (isinstance(node, ast.Set) or isinstance(node, ast.Dict)
                and any(not isinstance(key, ast.Constant) or type(key.value) not in (str, int, bool, type(None))
                        for key in node.keys)):
            self.add_boundary('context_exit_data_protocol_unmodeled', node, env, affected_scope='unknown')
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_01(self, node, env):
        if isinstance(node, ast.Name):
            if self.context_execution and not env.get(node.id):
                self.add_boundary('context_exit_name_unresolved', node, env, affected_scope='unknown')
            if node.id in env:
                if env[node.id] and all(value.get('kind') == 'import' for value in env[node.id]):
                    classes = self.class_values(env[node.id], env=env)
                    if classes:
                        return self.marked(classes, node)
                return env[node.id]
            imported = self.analyzer.imports.get(self.ref.module, {}).get(node.id)
            stable_import = not imported or self.analyzer._stable_import_name(
                self.ref.module + '.' + node.id)
            class_target = self.analyzer._class_symbol(
                imported or self.ref.module + '.' + node.id) if stable_import else None
            if class_target is not None:
                return [self.class_value(class_target[0], node, env)]
            target = self.analyzer._resolve(self.ref, node.id)
            if target and stable_import:
                return [self.callable_value(target[0], node)]
            if imported:
                return [{'kind': 'import', 'source': imported, 'relation': 'direct',
                         'import_modified': not stable_import,
                         'evidence': [self.evidence(node)],
                         'conditions': list(self.conditions)}]
            return []
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_02(self, node, env):
        if isinstance(node, ast.Attribute):
            attribute = self.attribute_key(node, env)
            if attribute is not None and attribute[0] in env:
                values = self.marked(env[attribute[0]], node)
                return [dict(value, attribute_provenance=[dict(fact, read=self.evidence(node))
                            for fact in value.get('attribute_provenance', [])]) for value in values]
            name = ast.unparse(node)
            first, dot, rest = name.partition('.')
            binding = env.get(first)
            if binding and all(value.get('kind') == 'import' and not any(
                    value.get(flag) for flag in ('import_modified', 'import_incomplete'))
                    for value in binding):
                identities = {value['source'] + dot + rest for value in binding}
                class_target = self.analyzer._class_symbol(next(iter(identities))) if len(identities) == 1 else None
            elif first not in env:
                imported = self.analyzer.imports.get(self.ref.module, {}).get(first)
                class_target = self.analyzer._class_symbol(
                    imported + dot + rest if imported else self.ref.module + '.' + name
                ) if not imported or self.analyzer._stable_import_name(
                    self.ref.module + '.' + first) else None
            else:
                class_target = None
            if class_target is not None:
                return [self.class_value(class_target[0], node, env)]
            qualified = None
            if binding and all(value.get('kind') == 'import' and not any(
                    value.get(flag) for flag in ('import_modified', 'import_incomplete'))
                    for value in binding):
                identities = {value['source'] + dot + rest for value in binding}
                qualified = next(iter(identities)) if len(identities) == 1 else None
            elif first not in env and self.analyzer._stable_import_name(self.ref.module + '.' + first):
                imported = self.analyzer.imports.get(self.ref.module, {}).get(first)
                qualified = imported + dot + rest if imported else None
            target = self.analyzer._resolve_import_binding(qualified) if qualified else None
            if target is not None:
                return [self.callable_value(target[0], node)]
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_03(self, node, env):
        if isinstance(node, ast.Constant):
            return []
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_04(self, node, env):
        if isinstance(node, (ast.Yield, ast.YieldFrom)):
            values = self.expression(node.value, env)
            if isinstance(node, ast.YieldFrom):
                values = self.project(values, '*', env)
            values = self.materialize(values, env)
            self.yields.extend(self.marked([
                dict(value, output_path=['*'] + value.get('output_path', []))
                for value in values], node, 'contained'))
            return []
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_05(self, node, env):
        if isinstance(node, ast.Lambda):
            positional = node.args.posonlyargs + node.args.args
            defaults = list(zip(positional[len(positional) - len(node.args.defaults):],
                                node.args.defaults))
            defaults += [(argument, default) for argument, default in
                         zip(node.args.kwonlyargs, node.args.kw_defaults) if default is not None]
            values = {argument.arg: self.expression(default, env)
                      for argument, default in defaults}
            target = FunctionRef(self.ref.module,
                self.ref.qualname + '.<lambda>@%s:%s' % (node.lineno, node.col_offset),
                self.ref.file_path, node.lineno)
            return [self.callable_value(target, node, values)]
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_06(self, node, env):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            key = '$heap:%s:%s:%s' % (self.ref.file_path, node.lineno, node.col_offset)
            items = []
            keys = []
            elements = list(zip(node.keys, node.values)) if isinstance(node, ast.Dict) else list(enumerate(node.elts))
            for index, element in elements:
                if isinstance(node, ast.Dict):
                    if index is None:
                        mapping = self.container_values(self.expression(element, env))
                        roots, unknown = self.affected_values(mapping, env)
                        self.mapping_effects.append({
                            'operation': 'merge', 'mapping': roots,
                            'element_path': ['*'], 'output_container': key,
                            'status': 'unknown_source' if unknown else 'bounded',
                            'conditions': list(self.conditions),
                            'evidence': self.evidence(element)})
                        copied = False
                        for reference in mapping:
                            if (reference.get('kind') == 'container'
                                    and reference.get('container_shape') == 'dict'):
                                items.extend(copy.deepcopy(env.get(reference['source'], [])))
                                keys.extend(copy.deepcopy(env.get(reference['source'] + '$keys', [])))
                                copied = True
                        if not copied:
                            values = self.marked(self.materialize(mapping, env), element, 'contained')
                            items.extend(dict(v, output_path=['*'] + v.get('output_path', []))
                                         for v in values)
                            keys.append({'kind': 'key', 'source': '*', 'key': '*'})
                        continue
                    slot = index.value if isinstance(index, ast.Constant) and isinstance(index.value, (str, int)) else '*'
                    key_values = self.marked(self.materialize(self.expression(index, env), env),
                                             index, 'contained')
                else:
                    slot = index if not isinstance(node, ast.Set) else '*'
                keys.append({'kind': 'key', 'source': repr(slot), 'key': slot})
                if isinstance(node, ast.Dict) and slot != '*':
                    updated = []
                    for value in items:
                        path = value.get('output_path', [None])
                        if path[0] == slot:
                            continue
                        if path[0] == '*':
                            value = dict(value, excluded_paths=_unique(
                                value.get('excluded_paths', []) + [[slot]]))
                        updated.append(value)
                    items = updated
                    for marker in keys[:-1]:
                        if marker['key'] == '*':
                            marker.setdefault('excluded_keys', []).append(slot)
                if isinstance(node, ast.Dict):
                    items.extend(dict(v, output_path=[slot] + v.get('output_path', []),
                                      container_role='key') for v in key_values)
                values = self.expression(element, env)
                items.extend(dict(v, output_path=[slot] + v.get('output_path', [])) for v in values)
            env[key] = items
            env[key + '$keys'] = keys
            reference = {'kind': 'container', 'source': key, 'container_shape': type(node).__name__.lower(),
                         'relation': 'direct', 'evidence': [self.evidence(node)], 'conditions': list(self.conditions)}
            literal = self.literal_fact(node, env)
            if literal is not None:
                reference['literal'] = literal
            return [reference]
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_07(self, node, env):
        if isinstance(node, ast.Subscript):
            raw = (self.module_dispatch(node.value.id, env)
                   if isinstance(node.value, ast.Name) else self.expression(node.value, env))
            values = self.container_values(raw)
            self.expression(node.slice, env)
            if isinstance(node.slice, (ast.Slice, ast.UnaryOp)):
                selected = []
                for value in values:
                    keys = env.get(value['source'] + '$keys', [])
                    slots = [k['key'] for k in keys]
                    if value.get('container_shape') not in ('list', 'tuple') or slots != list(range(len(slots))):
                        selected.extend(self.project([value], '*', env))
                        continue
                    try:
                        if isinstance(node.slice, ast.Slice):
                            bounds = [ast.literal_eval(n) if n is not None else None
                                      for n in (node.slice.lower, node.slice.upper, node.slice.step)]
                            indices = list(range(len(slots)))[slice(*bounds)]
                            for position, index in enumerate(indices):
                                selected.extend(dict(v, output_path=[position] + v.get('output_path', []))
                                                for v in self.project([value], index, env))
                        else:
                            index = ast.literal_eval(node.slice)
                            index = list(range(len(slots)))[index]
                            selected.extend(self.project([value], index, env))
                    except IndexError:
                        pass
                    except (ValueError, TypeError):
                        selected.extend(self.project([value], '*', env))
                return self.marked(selected, node)
            index = node.slice.value if isinstance(node.slice, ast.Constant) else '*'
            return self.marked(self.project(values, index, env), node)
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_08(self, node, env):
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp)) and not any(g.is_async for g in node.generators):
            local = copy.deepcopy(env)
            for generator in node.generators:
                iterable = self.expression(generator.iter, local)
                if iterable and all(v['kind'] == 'container' and
                                    local.get(v['source'] + '$keys') == [] for v in iterable):
                    return []
                values = self.project(iterable, '*', local)
                self.assign_target(generator.target, values, local, generator.target)
                for condition in generator.ifs:
                    self.expression(condition, local)
                    if isinstance(condition, ast.Constant) and not condition.value:
                        return []
                    if not self.refine_guard(condition, local):
                        return []
            elements = [node.key, node.value] if isinstance(node, ast.DictComp) else [node.elt]
            values = [v for element in elements for v in self.materialize(self.expression(element, local), local)]
            for key in set(env) | set(local):
                if key.startswith('$heap:'):
                    env[key] = _unique(env.get(key, []) + local.get(key, []))
            return self.marked([dict(v, output_path=['*'] + v.get('output_path', [])) for v in values], node, 'contained')
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_09(self, node, env):
        if isinstance(node, ast.IfExp):
            self.expression(node.test, env)
            before = list(self.conditions)
            positive, negative = copy.deepcopy(env), copy.deepcopy(env)
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': True}]
            possible_left = self.refine_guard(node.test, positive)
            left = self.marked(self.expression(node.body, positive), node.body) if possible_left else []
            self.conditions = before + [{'test': self.evidence(node.test), 'branch': False}]
            possible_right = self.refine_guard(node.test, negative, positive=False)
            right = self.marked(self.expression(node.orelse, negative), node.orelse) if possible_right else []
            env.clear()
            env.update(_merge_env(([positive] if possible_left else [])
                                  + ([negative] if possible_right else [])))
            self.conditions = before
            values = left + right
            if possible_left and not left or possible_right and not right:
                values = [dict(value, value_incomplete=True) for value in values]
            return values
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_10(self, node, env):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1
                and isinstance(node.ops[0], (ast.In, ast.NotIn))
                and len(node.comparators) == 1):
            key_values = self.expression(node.left, env)
            compared_values = self.expression(node.comparators[0], env)
            mappings = self.container_values(compared_values)
            if mappings and all(value.get('kind') == 'container'
                                and value.get('container_shape') == 'dict'
                                for value in mappings):
                try:
                    key = ast.literal_eval(node.left)
                except (ValueError, TypeError):
                    key = '*'
                roots, unknown = self.affected_values(mappings, env)
                self.mapping_effects.append({
                    'operation': 'membership', 'mapping': roots,
                    'element_path': [key], 'state_after': 'unchanged',
                    'status': 'unknown_key' if key == '*' or unknown else 'bounded',
                    'conditions': list(self.conditions),
                    'evidence': self.evidence(node)})
                return self.marked(
                    self.materialize(mappings, env) + key_values,
                    node, 'derived')
            # Both operands have already executed, even when their shape is
            # unknown. Falling through to generic traversal repeats effects
            # and can replace the first invocation's target/binding facts.
            return self.marked(self.materialize(key_values, env)
                               + self.materialize(compared_values, env), node, 'derived')
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_11(self, node, env):
        if isinstance(node, ast.BoolOp):
            current = copy.deepcopy(env)
            before = list(self.conditions)
            values = []
            exits = []
            for operand in node.values:
                values.extend(self.marked(self.materialize(self.expression(operand, current), current), operand))
                exits.append(copy.deepcopy(current))
                self.conditions = self.conditions + [{'test': self.evidence(operand), 'branch': isinstance(node.op, ast.And)}]
                if not self.refine_guard(operand, current, positive=isinstance(node.op, ast.And)):
                    break
            env.clear()
            env.update(_merge_env(exits))
            self.conditions = before
            return values
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_12(self, node, env):
        if isinstance(node, ast.Call):
            return self.call_expression(node, env)
        return None

    ## Evaluate one syntax-specific expression form when applicable.
    ## 若语法形式匹配，则执行对应的表达式传播。
    #
    #  @param node Expression syntax under evaluation.
    #  @param env Current abstract environment.
    #  @return Dependency alternatives or None when another handler should run.
    def _expression_part_13(self, node, env):
        if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            self.result.boundaries.append({'function': asdict(self.ref), 'reason': 'unsupported_expression', 'evidence': self.evidence(node)})
            return []
        return None
