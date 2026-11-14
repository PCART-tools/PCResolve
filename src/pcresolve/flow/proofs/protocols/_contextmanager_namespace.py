## @package pcresolve.flow.proofs.protocols._contextmanager_namespace
#  Standard contextmanager function construction, excluding future with effects.
#  标准 contextmanager 函数构造模型，不包含未来 with 执行产生的效果。

import ast

from pcresolve.flow.proofs.classes._class_partial import _namespace as functools_namespace
from pcresolve.flow.proofs.callables._function_observation import nonobserving_source
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit


## Check whether contextlib namespace uses remain stable in the source snapshot.
## 检查源码快照中的 contextlib 命名空间使用是否保持稳定。
#
#  @param analyzer Analyzer containing the fixed modules and import bindings.
#  @param require_nonobserving Whether to require an observer-isolation premise.
#  @return True only when all inspected contextlib uses satisfy the contract.
def _namespace(analyzer, require_nonobserving=True):
    cache_name = ('_contextmanager_namespace_premise' if require_nonobserving
                  else '_contextmanager_namespace_protocol_premise')
    cached = getattr(analyzer, cache_name, None)
    if cached is not None:
        return cached

    # Seed a conservative result before traversing modules to prevent re-entry loops.
    # 遍历模块前先写入保守结果，避免检查过程重入形成循环。
    setattr(analyzer, cache_name, False)
    if 'contextlib' in analyzer.module_bodies or analyzer.index_boundaries:
        return False
    inspected = 0
    protected = {'contextlib.contextmanager', 'contextlib.wraps'}
    for module, bodies in analyzer.module_bodies.items():
        aliases = {name: value for name, value in analyzer.imports.get(module, {}).items()
                   if value == 'contextlib' or value in protected}
        if any(not analyzer._stable_import_name(module + '.' + name)
               or not unmodified(analyzer, module + '.' + name) for name in aliases):
            return False
        for _, body in bodies:
            parents = {}
            nodes = []
            for statement in body:
                for node in ast.walk(statement):
                    inspected += 1

                    # Stop on oversized snapshots before the namespace proof becomes unbounded.
                    # 命名空间证明遍历过大快照前先停止，保持分析开销有界。
                    if inspected > 1000000:
                        raise _ClassEffectLimit()
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    nodes.append(node)
                    parents.update((child, node) for child in ast.iter_child_nodes(node))
            for node in nodes:
                if (isinstance(node, ast.Call) and node.args
                        and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'contextlib'
                        and (isinstance(node.func, ast.Name) and node.func.id == '__import__'
                             or isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module')):
                    return False
                if isinstance(node, ast.ImportFrom) and node.module == 'contextlib' and any(
                        alias.name == '*' for alias in node.names):
                    return False
                if not isinstance(node, ast.Name) or node.id not in aliases:
                    continue
                if not isinstance(node.ctx, ast.Load):
                    return False
                canonical, current = aliases[node.id], node
                if canonical == 'contextlib':
                    current = parents.get(node)
                    if not isinstance(current, ast.Attribute) or current.value is not node:
                        return False
                    if current.attr.startswith('__'):
                        return False
                    canonical += '.' + current.attr
                if canonical not in protected:
                    continue
                use = parents.get(current)
                if (not isinstance(current.ctx, ast.Load) or not (
                        isinstance(use, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and current in use.decorator_list)):
                    return False
    if (not unmodified(analyzer, 'contextlib.contextmanager')
            or not unmodified(analyzer, 'contextlib.wraps')
            or not functools_namespace(analyzer, ('wraps', 'update_wrapper', 'partial',
                                                  'WRAPPER_ASSIGNMENTS', 'WRAPPER_UPDATES'))
            or require_nonobserving and nonobserving_source(analyzer) is None):
        return False
    setattr(analyzer, cache_name, True)
    return True


## Prove only creation of a native helper by the imported contextmanager decorator.
## 仅证明已导入的 contextmanager 装饰器会创建原生辅助函数。
#
#  @param analyzer Fixed source snapshot and query budget.
#  @param owner Class identity before its namespace is bound to the class object.
#  @param member Fresh method with one decorator, whose inputs are checked separately.
#  @param shadowed Prior class namespace bindings.
#  @param dependencies Optional set of source files supporting this construction.
#  @param assumptions Optional set collecting the observer isolation premises.
#  @return Standard construction premise, never generator-body execution evidence.
def contextmanager_declaration(analyzer, owner, member, shadowed, dependencies=None, assumptions=None):
    if member.name in ('__init__', '__new__') or len(member.decorator_list) != 1:
        return None
    expression = member.decorator_list[0]
    if not isinstance(expression, (ast.Name, ast.Attribute)):
        return None
    name = ast.unparse(expression)
    head, dot, rest = name.partition('.')
    imported = analyzer.imports.get(owner.module, {}).get(head, '')
    if (head in shadowed or imported + (dot + rest if dot else '') != 'contextlib.contextmanager'
            or not analyzer._stable_import_name(owner.module + '.' + head)
            or not _namespace(analyzer, require_nonobserving=False)):
        return None
    stable, paths = _stable_builtin_namespace(analyzer, owner, ('getattr', 'setattr', 'AttributeError'))
    if not stable:
        return None
    if dependencies is not None:
        dependencies.update(paths)
    if assumptions is not None:
        assumptions.update(('standard_library_contextmanager_protocol',
            'standard_library_functools_wrapper_metadata_protocol',
            'no_external_monkeypatch_or_import_hook', 'source_snapshot_bindings_hold'))
    return 'stdlib_contextmanager_function_construction'
