## @package pcresolve.flow.proofs.namespaces.metadata._metadata_namespace
#  Stable stdlib metadata entry points; no source module is imported or executed.
#  验证标准库元数据入口的稳定性，不导入或执行目标源码模块。

import ast
import builtins

from pcresolve.flow.proofs.protocols._runtime_namespace import unmodified
from pcresolve.facts.import_facts import import_facts
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace


## Guard the builtin dependencies used inside standard metadata implementations.
## 守卫标准元数据实现使用的内置依赖。
#
#  @param analyzer Fixed source snapshot and shared syntax budget.
#  @param owner Source owner supplying evidence and namespace checks.
#  @return Stability and audited paths, or the existing class-effect budget signal.
def builtin_namespace(analyzer, owner):
    if analyzer.index_boundaries:
        return False, ()
    protected = tuple(sorted({name for name in vars(builtins) if not name.startswith('_')}
                             | {'__build_class__'}))
    return _stable_builtin_namespace(analyzer, owner, protected)


## Audit stdlib entry points and module capabilities in the fixed source scope.
## 在固定源码范围内审查标准库入口和模块能力。
#
#  @param analyzer Fixed primary snapshot and shared resource checkpoints.
#  @param module Standard library module supplying the modeled entry points.
#  @param names Exact modeled attribute names; unrelated attribute reads are allowed.
#  @return Source-path tuple on success, otherwise None.
def namespace(analyzer, module, names):
    key = module, tuple(sorted(names))
    cache = analyzer._metadata_stdlib_namespace
    if key in cache:
        return cache[key]
    # A partial or interrupted scan cannot become a positive cached premise.
    # 部分完成或中断的扫描不能成为肯定的缓存前提。
    cache[key] = None
    if analyzer.index_boundaries or module in analyzer.module_bodies:
        return None
    protected = {module + '.' + name for name in names}
    paths, count = set(), 0
    for owner, bodies in analyzer.module_bodies.items():
        for path, body in bodies:
            paths.add(path)
            aliases, nodes, parents = {}, [], {}
            for statement in body:
                for node in ast.walk(statement):
                    count += 1
                    if count > 1000000:
                        return None
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    nodes.append(node)
                    parents.update((child, node) for child in ast.iter_child_nodes(node))
                    for fact in import_facts(node):
                        if fact.kind == 'import' and fact.name == module:
                            aliases[fact.python_binding] = module
                        elif fact.kind == 'from' and not fact.level and fact.module == module:
                            if fact.name == '*' or fact.name.startswith('_'):
                                return None
                            if fact.name in names:
                                aliases[fact.python_binding] = module + '.' + fact.name
            for node in nodes:
                if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
                        and node.value.attr == 'modules' and isinstance(node.slice, ast.Constant)
                        and node.slice.value == module):
                    return None
                if (isinstance(node, ast.Call) and node.args
                        and isinstance(node.args[0], ast.Constant) and node.args[0].value == module
                        and (isinstance(node.func, ast.Name) and node.func.id == '__import__'
                             or isinstance(node.func, ast.Attribute)
                             and node.func.attr == 'import_module')):
                    return None
                if not isinstance(node, ast.Name) or node.id not in aliases:
                    continue
                if not isinstance(node.ctx, ast.Load):
                    return None
                current, canonical = node, aliases[node.id]
                if canonical == module:
                    current = parents.get(node)
                    if (not isinstance(current, ast.Attribute) or current.value is not node
                            or current.attr.startswith('_')
                            or not isinstance(current.ctx, ast.Load)):
                        return None
                    canonical += '.' + current.attr
                if canonical in protected:
                    use = parents.get(current)
                    # A bare decorator is an immediate invocation just like a
                    # Call.func use. It does not publish the entry-point object.
                    # 裸装饰器也会立即调用入口，不会因此暴露入口对象。
                    invoked = (isinstance(use, ast.Call) and use.func is current
                               or isinstance(use, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                               and current in use.decorator_list)
                    if not isinstance(current.ctx, ast.Load) or not invoked:
                        return None
            if any(alias in analyzer.imports.get(owner, {})
                   and not analyzer._stable_import_name(owner + '.' + alias) for alias in aliases):
                return None
    if any(not unmodified(analyzer, name) for name in protected):
        return None
    cache[key] = tuple(sorted(paths))
    return cache[key]
