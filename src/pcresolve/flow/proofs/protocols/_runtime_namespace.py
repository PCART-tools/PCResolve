## @package pcresolve.flow.proofs.protocols._runtime_namespace
#  Track possible module-binding writes.
#
#
#  Possible source writes to import-backed module bindings, without execution.
#  不执行源码，检查对导入来源模块绑定的可能写入。



import ast
from dataclasses import asdict

from pcresolve.facts.import_facts import import_facts, resolve_relative_module

# Matplotlib's fixed source snapshot is over one million AST nodes once both
# binding collection and write/escape checks are counted. Exhaustion must remain
# a boundary, but the previous cap was below the size of common library trees.
_LIMIT = 10_000_000


## Locate reflective and imported-module export writes in the fixed source set.
## 在固定源码集合中定位反射写入和导入模块导出写入。
#
#  @param analyzer Indexed source files, definitions and module bodies.
#  @return Module/name sets and source witnesses, or None for exhausted syntax work.
def writes(analyzer):
    if analyzer._runtime_namespace_cache is not False:
        return analyzer._runtime_namespace_cache
    analyzer._runtime_namespace_cache = None
    changed, evidence, count = {}, [], [0]
    definitions = {node: ref for ref, node in analyzer.definitions}
    module_names = set(analyzer.module_bodies)
    class_names = {ref.module + '.' + ref.qualname for ref, _ in analyzer.classes}

    ## Record a possible namespace write and its source witness.
    ## 记录可能的命名空间写入及其源码证据。
    #
    #  @param module Qualified module or class namespace.
    #  @param name Written name or wildcard.
    #  @param ref Enclosing source identity.
    #  @param node AST node witnessing the write.
    #  @return None
    def changed_at(module, name, ref, node):
        changed.setdefault(module, set()).add(name)
        evidence.append({'module': module, 'name': name, 'function': asdict(ref),
            'evidence': {'file_path': ref.file_path, 'lineno': node.lineno,
                'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
                'end_col_offset': node.end_col_offset}})

    for module, bodies in analyzer.module_bodies.items():
        for path, body in bodies:
            imports, namespaces = {}, {}
            for statement in body:
                for node in ast.walk(statement):
                    count[0] += 1
                    if count[0] > _LIMIT:
                        return None
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    for fact in import_facts(node):
                        imported = (fact.name if fact.kind == 'import' else resolve_relative_module(
                            module, path.endswith('__init__.py'), fact.module, fact.level)
                            + '.' + fact.name)
                        if fact.kind == 'import':
                            module_names.add(imported)
                            if not fact.asname:
                                imported = imported.partition('.')[0]
                                module_names.add(imported)
                        imports.setdefault(fact.python_binding, set()).add(imported)
            ref_type = type(next(iter(definitions.values()))) if definitions else None
            if ref_type is None:
                # No source callable can depend on a module-only input set.
                continue
            module_ref = ref_type(module, '', path)

            ## Resolve supported module, class or namespace-dictionary references.
            ## 解析受支持的模块、类或命名空间字典引用。
            #
            #  @param value Candidate source expression.
            #  @return Set of qualified namespace and kind pairs.
            def reference(value):
                if isinstance(value, ast.Name):
                    names = set(imports.get(value.id, ())) | {module + '.' + value.id}
                    return set(namespaces.get(value.id, ())) | {
                        (name, 'module' if name in module_names else 'class') for name in names
                        if name in module_names | class_names}
                if isinstance(value, ast.Attribute):
                    return {(owner + '.' + value.attr, 'module' if owner + '.' + value.attr in
                             module_names else 'class') for owner, kind in reference(value.value)
                            if kind in ('module', 'class')
                            and owner + '.' + value.attr in module_names | class_names}
                if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                        and value.func.id == 'globals' and not value.args and not value.keywords):
                    return {(module, 'dictionary')}
                if (isinstance(value, ast.Subscript) and isinstance(value.value, ast.Attribute)
                        and value.value.attr == 'modules'):
                    owners = reference(value.value.value)
                    if ('sys', 'module') in owners:
                        name = (value.slice.value if isinstance(value.slice, ast.Constant)
                                and type(value.slice.value) is str else module if isinstance(
                                    value.slice, ast.Name) and value.slice.id == '__name__' else None)
                        return {(name, 'module')} if name is not None else set()
                return set()

            ## Visit syntax and record writes under its enclosing callable scope.
            ## 遍历语法并记录所属可调用作用域内的写入。
            #
            #  @param node Source AST node.
            #  @param ref Enclosing source identity.
            #  @param scope Enclosing callable AST, or None at module level.
            #  @return None; budget exhaustion raises OverflowError.
            def visit(node, ref, scope=None):
                count[0] += 1
                if count[0] > _LIMIT:
                    raise OverflowError()
                if analyzer._analysis_budget is not None:
                    analyzer._analysis_budget.checkpoint()
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                    ref = definitions.get(node, ref)
                    scope = node
                if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
                    if scope is not None and node.id in analyzer._scope_facts(scope).globals:
                        changed_at(module, node.id, ref, node)
                if isinstance(node, (ast.Attribute, ast.Subscript)) and isinstance(
                        node.ctx, (ast.Store, ast.Del)):
                    for owner, kind in reference(node.value):
                        if isinstance(node, ast.Attribute) and kind in ('module', 'class'):
                            changed_at(owner, node.attr, ref, node)
                        elif isinstance(node, ast.Subscript) and kind == 'dictionary':
                            name = (node.slice.value if isinstance(node.slice, ast.Constant)
                                    and type(node.slice.value) is str else '*')
                            if scope is not None or name != '*':
                                changed_at(owner, name, ref, node)
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id in ('setattr', 'delattr'):
                        if len(node.args) >= 2:
                            name = (node.args[1].value if isinstance(node.args[1], ast.Constant)
                                    and type(node.args[1].value) is str else '*')
                            for owner, kind in reference(node.args[0]):
                                if kind in ('module', 'class'):
                                    changed_at(owner, name, ref, node)
                    if isinstance(node.func, ast.Attribute):
                        for owner, kind in reference(node.func.value):
                            if kind != 'dictionary' or node.func.attr not in (
                                    'update', 'setdefault', 'pop', 'clear', '__setitem__', '__delitem__'):
                                continue
                            # A module-initialization update builds its snapshot
                            # exports. Runtime updates cannot inherit that premise.
                            # 模块初始化更新建立快照导出；运行时更新不能沿用该前提。
                            if scope is None and node.func.attr == 'update':
                                continue
                            names = []
                            if node.func.attr == 'update' and len(node.args) == 1 and isinstance(
                                    node.args[0], ast.Dict) and all(isinstance(key, ast.Constant)
                                    and type(key.value) is str for key in node.args[0].keys):
                                names = [key.value for key in node.args[0].keys]
                            elif node.args and isinstance(node.args[0], ast.Constant) and type(
                                    node.args[0].value) is str:
                                names = [node.args[0].value]
                            names += [keyword.arg for keyword in node.keywords if keyword.arg is not None]
                            for name in names or ['*']:
                                changed_at(owner, name, ref, node)
                for child in ast.iter_child_nodes(node):
                    visit(child, ref, scope)
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    refs = reference(node.value)
                    if refs:
                        for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
                            if isinstance(target, ast.Name):
                                namespaces.setdefault(target.id, set()).update(refs)

            try:
                for statement in body:
                    visit(statement, module_ref)
            except OverflowError:
                return None

    # Cache only a completed scan; exhaustion leaves the conservative sentinel.
    # 仅缓存完整扫描；预算耗尽时保留保守的未确认标记。
    result = changed, evidence
    analyzer._runtime_namespace_cache = result
    return result


## Check that no bounded source writer can change this namespace lookup prefix.
## 检查有界源码写入是否可能改变该命名空间查找前缀。
#
#  @param analyzer Fixed source generation and per-query writer cache.
#  @param qualified Import-backed name, including optional class/method suffixes.
#  @return False for a possible write or scan exhaustion; True is not runtime binding evidence.
def unmodified(analyzer, qualified):
    result = writes(analyzer)
    if result is None:
        return False
    names = qualified.split('.')
    for index in range(1, len(names)):
        changed = result[0].get('.'.join(names[:index]), ())
        if '*' in changed or names[index] in changed:
            return False
    return True
