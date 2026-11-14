## @package pcresolve.flow.proofs.callables.decorators._decorator_imports
#  Conditional cached source imports reached while decorating a fresh function.
#  建模新鲜函数装饰期间触达的条件式缓存源码导入。

import ast
from dataclasses import asdict, replace

from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.facts.import_facts import import_facts, resolve_relative_module
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.flow.proofs.namespaces.modules._module_getattr import missing as module_getattr_missing

_DECORATOR_IMPORT_NODE_LIMIT = 100000


## Build a source span record for one import or lookup operation.
## 为一次导入或查找操作构造源码范围记录。
#
#  @param ref Source reference carrying the file path.
#  @param node AST node carrying the source coordinates.
#  @return Dictionary containing the node's start and end positions.
def _span(ref, node):
    return {'file_path': ref.file_path, 'lineno': node.lineno,
            'col_offset': node.col_offset, 'end_lineno': node.end_lineno,
            'end_col_offset': node.end_col_offset}


## Resolve the module named by one parsed import fact.
## 解析一个导入事实所指向的模块。
#
#  @param ref Source module reference providing package context.
#  @param statement Import statement containing the fact.
#  @param fact Parsed import fact.
#  @return Absolute imported module name.
def _imported_module(ref, statement, fact):
    if fact.kind == 'import':
        return fact.name
    return resolve_relative_module(ref.module, ref.file_path.endswith('__init__.py'),
                                   fact.module, fact.level)


## Validate a narrowly read-only globals().get lookup.
## 验证有限形式的只读 globals().get 查找。
#
#  @param analyzer Analyzer providing builtin binding facts.
#  @param ref Source reference used to locate the enclosing scope.
#  @param node Candidate globals name expression.
#  @param parents AST parent map for the captured source tree.
#  @param protected Keys that cannot be read through this fallback.
#  @return True when the expression is a stable, unprotected globals lookup.
def _readonly_globals(analyzer, ref, node, parents, protected):
    call = parents.get(node)
    if not (isinstance(call, ast.Call) and call.func is node and not call.args and not call.keywords):
        return False
    method = parents.get(call)
    read = parents.get(method)
    if not (isinstance(method, ast.Attribute) and method.value is call and method.attr == 'get'
            and isinstance(read, ast.Call) and read.func is method and len(read.args) == 1
            and not read.keywords and isinstance(read.args[0], ast.Constant)
            and type(read.args[0].value) is str and read.args[0].value not in protected):
        return False
    scope, names, current = None, [], node
    while current in parents:
        current = parents[current]
        if isinstance(current, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            if any(isinstance(item, ast.Name) and item.id == 'globals'
                   for generator in current.generators for item in ast.walk(generator.target)):
                return False
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            if scope is None:
                scope = current
            names.append(getattr(current, 'name', '<lambda>'))
    owner = replace(ref, qualname='.'.join(reversed(names)))
    return analyzer._builtin_name_status(owner, scope, 'globals',
        definition_scope=scope is None) == 'confirmed_builtin'


## Check whether the cached-import namespace remains closed and unmodified.
## 检查缓存导入涉及的命名空间是否封闭且未被修改。
#
#  @param analyzer Analyzer containing all relevant source modules.
#  @param refs Source references whose namespaces participate in the lookup.
#  @param module Target module whose export bindings must remain stable.
#  @return True only when imports, aliases, and namespace uses stay bounded.
def _namespace_stable(analyzer, refs, module):
    cache = getattr(analyzer, '_decorator_import_namespace_cache', None)
    if cache is None:
        cache = analyzer._decorator_import_namespace_cache = {}
    key = (tuple(sorted(ref.module for ref in refs)), module)
    if key in cache:
        return cache[key]

    # Seed a conservative result to prevent recursive namespace checks.
    # 先写入保守占位结果，避免命名空间检查递归重入。
    cache[key] = False
    count = 0
    for ref in refs:
        bodies = analyzer.module_bodies.get(ref.module, [])
        if len(bodies) != 1:
            return False
        nodes, parents = [], {}
        for statement in bodies[0][1]:
            for node in ast.walk(statement):
                count += 1

                # Bound the source-wide namespace audit and honor cancellation budgets.
                # 限制源码命名空间审计规模，并遵守协作式取消预算。
                if count > _DECORATOR_IMPORT_NODE_LIMIT:
                    return False
                if analyzer._analysis_budget is not None:
                    analyzer._analysis_budget.checkpoint()
                nodes.append(node)
                for child in ast.iter_child_nodes(node):
                    parents[child] = node
        aliases = {}
        for node in nodes:
            for fact in import_facts(node):
                imported = _imported_module(ref, node, fact)
                canonical = (imported if fact.kind == 'import' else imported + '.' + fact.name)
                if fact.kind == 'import' and not fact.asname:
                    canonical = imported.partition('.')[0]
                aliases.setdefault(fact.python_binding, set()).add(canonical)
        for node in nodes:
            if isinstance(node, ast.ImportFrom) and any(alias.name == '*' for alias in node.names):
                return False
            if isinstance(node, ast.Name) and node.id in (
                    '__builtins__', 'exec', 'eval', 'globals', 'locals', 'vars', '__import__'):
                if node.id != 'globals' or not _readonly_globals(analyzer, ref, node, parents,
                        {module.rpartition('.')[2], '__getattr__', '__class__', '__path__', '__builtins__'}):
                    return False
            if not isinstance(node, ast.Name) or node.id not in aliases:
                continue
            for canonical in aliases[node.id]:
                current = node
                qualified = canonical
                # A namespace alias must be used only through ordinary reads.
                # Writes to fields of exported class/instance objects are not
                # writes to the module's export binding.
                relevant = module == canonical or module.startswith(canonical + '.')
                while True:
                    if qualified == 'sys.modules':
                        use = parents.get(current)
                        read = parents.get(use)
                        if (isinstance(use, ast.Attribute) and use.attr == 'get'
                                and isinstance(read, ast.Call) and read.func is use
                                and len(read.args) == 1 and not read.keywords
                                and isinstance(read.args[0], ast.Constant)
                                and type(read.args[0].value) is str
                                and module != read.args[0].value
                                and not module.startswith(read.args[0].value + '.')):
                            break
                        return False
                    if (qualified.startswith(module + '.')
                            and qualified.count('.') == module.count('.') + 1
                            and isinstance(getattr(current, 'ctx', None), ast.Load)
                            and analyzer._resolve_import_binding(qualified) is not None):
                        use = parents.get(current)
                        if not (isinstance(use, ast.Call) and use.func is current
                                or isinstance(use, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                                and current in use.decorator_list
                                or isinstance(use, ast.Attribute) and use.value is current
                                and use.attr in ('__doc__', '__name__', '__qualname__')
                                and isinstance(use.ctx, ast.Load)):
                            return False
                    if relevant and isinstance(getattr(current, 'ctx', None), (ast.Store, ast.Del)):
                        return False
                    parent = parents.get(current)
                    if isinstance(parent, ast.Attribute) and parent.value is current:
                        if relevant and parent.attr in (
                                '__dict__', '__class__', '__path__', '__getattr__', '__getattribute__',
                                '__loader__', '__spec__', '__builtins__', '__import__'):
                            return False
                        if qualified.startswith(module + '.') and (
                                parent.attr in ('__globals__', '__closure__', '__dict__')
                                or parent.attr in ('__code__', '__defaults__', '__kwdefaults__')
                                and isinstance(parent.ctx, (ast.Store, ast.Del))):
                            return False
                        qualified += '.' + parent.attr
                        current = parent
                        relevant = module == qualified or module.startswith(qualified + '.')

                        # Assigning/deleting a direct export changes lookup.
                        # 对直接导出项赋值或删除会改变模块查找结果。
                        if qualified.startswith(module + '.') and qualified.count('.') == module.count('.') + 1:
                            if isinstance(parent.ctx, (ast.Store, ast.Del)):
                                return False
                        continue
                    if relevant:
                        # A bare module passed to a helper, saved in an alias,
                        # reflected or returned loses the bounded namespace.
                        return False
                    break
    cache[key] = True
    return True


## Bind a local from-import under the decorated entry's prior initialization.
## 在被装饰入口此前的初始化条件下绑定局部 from-import。
#
#  @param proof Bounded decorator analysis; no analyzed module is executed.
#  @param ref Callback source identity containing the local import.
#  @param node Reached ast.ImportFrom statement.
#  @return Conditional binding fact with initialization, namespace and source evidence.
def cached_import(proof, ref, node):
    analyzer = proof.analyzer
    if (not isinstance(node, ast.ImportFrom) or node.level or not node.module
            or not node.names or len(node.names) > 32
            or any(alias.name == '*' for alias in node.names) or analyzer.index_boundaries):
        return None
    entry = proof.ref
    entry_bodies = analyzer.module_bodies.get(entry.module, [])
    target_bodies = analyzer.module_bodies.get(node.module, [])
    if len(entry_bodies) != 1 or len(target_bodies) != 1:
        return None
    initialized = []
    package_lookups = []
    package_refs = {}
    for statement in entry_bodies[0][1]:
        if statement.lineno >= entry.lineno:
            break
        for fact in import_facts(statement):
            if not analyzer._stable_import_name(entry.module + '.' + fact.python_binding):
                continue
            module = _imported_module(entry, statement, fact)
            child = module + '.' + fact.name if fact.kind == 'from' else module
            direct = module == node.module or module.startswith(node.module + '.')
            submodule = child == node.module and node.module in analyzer.module_bodies
            if submodule and not direct:
                package = analyzer.import_binding_facts.get(module, [])
                if (len(package) != 1 or package[0].get(fact.name)
                        or any(package[0].get(name) for name in (
                            '__class__', '__path__', '__loader__', '__spec__'))):
                    continue
                if package[0].get('__getattr__'):
                    missing = module_getattr_missing(analyzer, module, fact.name)
                    if missing is None:
                        continue
                    if missing not in package_lookups:
                        package_lookups.append(missing)
                package_bodies = analyzer.module_bodies.get(module, [])
                if len(package_bodies) != 1:
                    continue
                package_refs[module] = type(ref)(module, '', package_bodies[0][0], 0)
            if direct or submodule:
                initialized.append(statement)
    if not initialized:
        return None

    # Reject target exports and package ancestors whose namespace hooks can redirect lookup.
    # 排除可能通过命名空间钩子重定向查找的目标导出和包祖先。
    path, body = target_bodies[0]
    if statement_scope_facts(body).bound & {'__getattr__', '__class__', '*'}:
        return None
    if any(not analyzer._stable_import_name(node.module + '.' + alias.name) for alias in node.names):
        return None
    target_ref = type(ref)(node.module, '', path, 0)
    parts = node.module.split('.')
    for length in range(1, len(parts)):
        parent = '.'.join(parts[:length])
        ancestors = analyzer.import_binding_facts.get(parent, [])
        if (len(ancestors) != 1 or any(ancestors[0].get(name) for name in (
                '__class__', '__path__', '__loader__', '__spec__'))):
            return None
    refs = {item.module: item for item in (entry, ref, target_ref)}
    refs.update(package_refs)
    if not _namespace_stable(analyzer, tuple(refs.values()), node.module):
        return None
    for lookup in package_lookups:
        if not _namespace_stable(analyzer, tuple(refs.values()), lookup['factory']['module']):
            return None
    try:
        stable, dependencies = _stable_builtin_namespace(analyzer, entry, ('__import__', 'globals'))
    except _ClassEffectLimit:
        return None
    if not stable:
        return None

    # Return conditional cache-binding evidence without claiming that import execution occurred.
    # 返回条件式缓存绑定证据，但不声称导入语句已实际执行。
    paths = set(dependencies) | {item.file_path for item in refs.values()}
    for lookup in package_lookups:
        paths.update(lookup['source_hashes'])
    return {'kind': 'source_cached_import_binding', 'function': asdict(ref),
        'status': 'bound_on_normal_cached_import_return', 'runtime_import_confirmed': False,
        'bindings': [{'name': alias.asname or alias.name, 'module': node.module,
                      'attribute': alias.name} for alias in node.names],
        'effects': 'module_execution_not_required_if_cache_preserved',
        'initialization_function': asdict(entry),
        'conditions': list(proof.conditions), 'evidence': _span(ref, node),
        'initialization_evidence': [_span(entry, statement) for statement in initialized],
        'package_lookups': package_lookups,
        'source_hashes': {path: analyzer.hashes[path] for path in sorted(paths)},
        'assumptions': sorted(set(['source_snapshot_bindings_hold', 'standard_builtin_import_binding',
            'initialized_source_module_cache_preserved', 'no_external_monkeypatch_or_import_hook',
            'no_unmodeled_indirect_module_mutation', 'standard_builtin_namespace_preserved']
            + [claim for lookup in package_lookups for claim in lookup['assumptions']]))}
