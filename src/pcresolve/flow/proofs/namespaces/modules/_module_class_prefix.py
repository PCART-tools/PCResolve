## @package pcresolve.flow.proofs.namespaces.modules._module_class_prefix
#  Fresh root-class namespace before a first bounded module-level call.
#  首次有界模块级调用前新建根类的命名空间。

import ast
import copy
from dataclasses import asdict

from pcresolve.flow.proofs.classes._class_definition import namespace_issues, _namespace_syntax
from pcresolve.flow.proofs.callables._function_factory import _canonical
from pcresolve.flow.proofs.callables._function_observation import nonobserving_source
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit


## Capture a node's complete position in the source class module.
## 捕获源码类所在模块中节点的完整位置。
#
#  @param ref Source class identity.
#  @param node AST node with source positions.
#  @return Source location dictionary.
def _span(ref, node):
    return {'file_path': ref.file_path, **{field: getattr(node, field) for field in
        ('lineno', 'col_offset', 'end_lineno', 'end_col_offset')}}


## Bound the fresh namespace before an explicit module call, not its effects.
## 有界证明显式模块调用前的新建命名空间，不证明调用效果。
#
#  @param analyzer Fixed source snapshot and shared class-evidence budget.
#  @param target Exact source root class declaration.
#  @param call Actual standalone module-call AST node.
#  @return Source prefix evidence or None for unknown intervening evaluation.
def module_class_prefix(analyzer, target, call):
    ref, cls = target
    bodies = analyzer.module_bodies.get(ref.module, [])
    if (len(bodies) != 1 or cls not in bodies[0][1] or cls.bases or cls.keywords
            or cls.decorator_list or analyzer.definition_conditions.get(ref)
            or not analyzer._stable_import_name(ref.module + '.' + ref.qualname)
            or analyzer.index_boundaries or not isinstance(call, ast.Call)
            or call.args or call.keywords or not isinstance(call.func, ast.Attribute)
            or not isinstance(call.func.value, ast.Name) or call.func.value.id != cls.name):
        return None
    cache = getattr(analyzer, '_module_class_prefix_cache', None)
    if cache is None:
        cache = analyzer._module_class_prefix_cache = {}
    key = (ref, call.lineno, call.col_offset, call.end_lineno, call.end_col_offset)
    if key in cache:
        return copy.deepcopy(cache[key])
    body = bodies[0][1]
    reached = [index for index, statement in enumerate(body)
               if isinstance(statement, ast.Expr) and statement.value is call]
    if len(reached) != 1 or reached[0] <= body.index(cls):
        return None
    assumptions, paths, evidence = set(), {ref.file_path}, []
    aliases = []

    ## Charge syntax traversal against the shared class-effect budget.
    ## 将语法遍历计入共享类效果预算。
    #
    #  @param node Source node to inspect.
    #  @return None; exhaustion raises _ClassEffectLimit.
    def charge(node):
        for _ in _namespace_syntax(node):
            analyzer._class_effect_fact_steps -= 1
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            if analyzer._class_effect_fact_steps < 0:
                raise _ClassEffectLimit()

    try:
        if not _stable_builtin_namespace(analyzer, ref, ('type', '__build_class__', 'object'))[0]:
            return None
        observation = nonobserving_source(analyzer)
        if observation is None:
            return None
        charge(cls)
        if namespace_issues(analyzer, [target], dependencies=paths, assumptions=assumptions):
            return None
        for statement in body[body.index(cls) + 1:reached[0]]:
            charge(statement)
            # Retaining Root in even a deferred function's default is an
            # immediate exposure. Its body alone has no prefix execution.
            # 延迟函数的默认值仍会立即求值，保存类引用会造成暴露。
            if any(isinstance(node, ast.Name) and node.id == cls.name
                   for node in _namespace_syntax(statement)):
                return None
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arguments = statement.args.posonlyargs + statement.args.args + statement.args.kwonlyargs
                arguments += [arg for arg in (statement.args.vararg, statement.args.kwarg) if arg]
                values = statement.args.defaults + [item for item in statement.args.kw_defaults if item]
                values += [item.annotation for item in arguments if item.annotation is not None]
                values += [statement.returns] if statement.returns is not None else []
                if statement.decorator_list or any(not isinstance(value, ast.Constant) for value in values):
                    return None
            elif isinstance(statement, ast.ClassDef):
                selected = analyzer._definition_index.find(ref.module, statement.name, kind='class')
                if (len(selected) != 1 or selected[0][1] is not statement or statement.bases
                        or statement.keywords or statement.decorator_list):
                    return None
                # Only independently modeled native declaration operations may
                # run after the protected class has become globally accessible.
                # 类暴露后只允许独立建模的原生声明操作。
                for node in _namespace_syntax(statement):
                    if isinstance(node, ast.Call) and _canonical(analyzer, ref, statement, node.func) not in (
                            're.compile', 'functools.lru_cache'):
                        return None
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if any(not (isinstance(decorator, ast.Name)
                                    and decorator.id in ('staticmethod', 'classmethod', 'property'))
                               and not isinstance(decorator, ast.Call) for decorator in node.decorator_list):
                            return None
                if namespace_issues(analyzer, selected, dependencies=paths, assumptions=assumptions):
                    return None
            elif isinstance(statement, ast.Assign):
                if any(not isinstance(destination, ast.Name) for destination in statement.targets):
                    return None
                if isinstance(statement.value, ast.Name):
                    name = statement.value.id
                    functions = analyzer._definition_index.find(ref.module, name)
                    if (len(functions) != 1 or functions[0][1] not in body
                            or not isinstance(functions[0][1], (ast.FunctionDef, ast.AsyncFunctionDef))
                            or functions[0][1].decorator_list
                            or functions[0][1].lineno >= statement.lineno
                            or not analyzer._stable_import_name(ref.module + '.' + name)):
                        return None
                    aliases.extend({'binding_name': destination.id, 'target': asdict(functions[0][0]),
                        'binding_evidence': _span(ref, statement), 'body_execution': 'deferred'}
                        for destination in statement.targets)
                    evidence.append(_span(ref, statement))
                    continue
                if any(isinstance(node, ast.Call) for node in ast.walk(statement.value)):
                    return None
                try:
                    ast.literal_eval(statement.value)
                except (ValueError, TypeError, RecursionError):
                    return None
            elif not isinstance(statement, ast.Pass) and not (
                    isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)):
                return None
            evidence.append(_span(ref, statement))
    except _ClassEffectLimit:
        return None

    # Publish only a normal-prefix premise; the call and later state are unproved.
    # 仅发布正常前缀前提，调用效果和后续状态仍未证明。
    assumptions.update(observation['assumptions'])
    assumptions.update(['source_snapshot_bindings_hold', 'builtin_type_class_creation_protocol',
        'source_module_fresh_class_prefix', 'no_external_monkeypatch_or_import_hook',
        'standard_builtin_namespace_preserved', 'no_unmodeled_indirect_builtin_mutation'])
    hashes = {**analyzer.hashes, **analyzer._supporting_source_hashes}
    result = {'kind': 'source_module_fresh_class_prefix', 'status': 'source_bound',
        'receiver_class': asdict(ref), 'phase': 'before_module_call',
        'class_evidence': _span(ref, cls), 'call_evidence': _span(ref, call),
        'intermediate_evidence': evidence, 'call_effects': 'unproved',
        'function_aliases': aliases,
        'deferred_bodies_executed': False, 'runtime_initialization_confirmed': False,
        'completion': 'normal_prefix_only', 'observation_guard': observation,
        'source_hashes': dict(sorted(hashes.items())), 'assumptions': sorted(assumptions)}
    cache[key] = copy.deepcopy(result)
    return result
