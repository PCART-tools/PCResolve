## @package pcresolve.flow.proofs.protocols._cached_imports
#  Analyze source-conditioned cached imports.
#
#
#  Source-conditioned cached imports, separate from arbitrary module execution.
#  基于源码条件描述缓存导入，不推断任意模块执行。



import ast
from dataclasses import asdict

from pcresolve.facts.import_facts import import_facts, resolve_relative_module
from pcresolve.facts.scope_facts import statement_scope_facts

_CACHED_IMPORT_NODE_LIMIT = 20000


## Describe a finite from-import whose module was loaded during source initialization.
## 描述源码初始化期间已加载模块上的有限 from-import。
#
#  @param analyzer Fixed source and ordinary namespace binding facts.
#  @param ref Function containing the reached import statement.
#  @param node Exact local import syntax.
#  @param evidence Source evidence constructor.
#  @param conditions Current flow path, without a reachability claim.
#  @return Conditional normal cached-import binding, or None; no runtime observation.
def cached_import(analyzer, ref, node, evidence, conditions):
    if (not isinstance(node, ast.ImportFrom) or node.level or not node.module
            or len(node.names) > 32 or any(alias.name == '*' for alias in node.names)):
        return None
    caller_bodies = analyzer.module_bodies.get(ref.module, [])
    target_bodies = analyzer.module_bodies.get(node.module, [])
    if len(caller_bodies) != 1 or len(target_bodies) != 1:
        return None
    # Establish that an earlier module-level import can populate the cache.
    # 确认此前的模块级导入可以填充缓存。
    initialized = []
    for statement in caller_bodies[0][1]:
        if statement.lineno >= ref.lineno:
            break
        for fact in import_facts(statement):
            module = fact.name if fact.kind == 'import' else resolve_relative_module(
                ref.module, caller_bodies[0][0].endswith('__init__.py'), fact.module, fact.level)
            if module == node.module or module.startswith(node.module + '.'):
                initialized.append(statement)
    if not initialized:
        return None
    # Reject visible dynamic namespace operations or cache writes conservatively.
    # 对可见的动态命名空间操作和缓存写入保守地拒绝建模。
    inspected = 0
    for statement in caller_bodies[0][1]:
        for child in ast.walk(statement):
            inspected += 1
            if inspected > _CACHED_IMPORT_NODE_LIMIT:
                return None
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            if (isinstance(child, ast.Name)
                    and child.id in ('__builtins__', 'exec', 'eval', 'globals', 'locals', 'vars')
                    or isinstance(child, ast.Attribute)
                    and child.attr in ('__import__', '__class__', '__getattr__',
                                       '__path__', '__dict__')
                    and isinstance(child.ctx, (ast.Store, ast.Del))):
                return None
            # A visible cache write contradicts the cached-import premise.
            if (isinstance(child, ast.Attribute) and child.attr == 'modules'
                    or isinstance(child, ast.ImportFrom) and child.module == 'sys'
                    and any(alias.name in ('modules', '*') for alias in child.names)
                    or isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
                    and child.func.id in ('setattr', 'delattr')):
                return None
    # The target's namespace must also remain stable under the supported model.
    # 目标模块的命名空间也必须在受支持的模型内保持稳定。
    target_path, target_body = target_bodies[0]
    bound = statement_scope_facts(target_body).bound
    if bound & {'__getattr__', '__class__', '*'}:
        return None
    for statement in target_body:
        for child in ast.walk(statement):
            inspected += 1
            if inspected > _CACHED_IMPORT_NODE_LIMIT:
                return None
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
            if (isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
                    and child.id in ('exec', 'eval', 'globals', 'locals', 'vars', '__import__')
                    or isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
                    and child.func.id in ('setattr', 'delattr')
                    or isinstance(child, ast.Attribute)
                    and isinstance(child.ctx, (ast.Store, ast.Del))):
                return None
    if any(not analyzer._stable_import_name(node.module + '.' + alias.name)
           for alias in node.names):
        return None
    paths = {ref.file_path, target_path}
    return {'kind': 'source_cached_import_binding', 'function': asdict(ref),
        'status': 'bound_on_normal_cached_import_return', 'runtime_import_confirmed': False,
        'bindings': [{'name': alias.asname or alias.name,
                      'module': node.module, 'attribute': alias.name} for alias in node.names],
        'effects': 'module_execution_not_required_if_cache_preserved',
        'conditions': list(conditions), 'evidence': evidence(node),
        'initialization_evidence': [evidence(statement) for statement in initialized],
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(paths)},
        'assumptions': ['source_snapshot_bindings_hold', 'standard_builtin_import_binding',
                        'initialized_source_module_cache_preserved',
                        'no_external_monkeypatch_or_import_hook',
                        'no_unmodeled_indirect_module_mutation']}
