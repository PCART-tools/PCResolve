## @package pcresolve.flow.proofs.namespaces.modules._module_getattr
#  Bounded missing-name obligations for a source module's property dispatch.
#  为源码模块的 property 分派建立有界的缺失名称义务。

import ast
from dataclasses import asdict

from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.flow.proofs.protocols._property_namespace import _stable_builtin_namespace
from pcresolve.facts.import_facts import import_facts


## Remove an optional leading function docstring from a statement body.
## 从语句体中移除可选的首个函数文档字符串。
#
#  @param node Function-like AST node whose body is inspected.
#  @return Body statements excluding a leading string expression.
def _body(node):
    return [statement for statement in node.body if not (
        isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str))]


## Check whether an expression is the exact requested name.
## 检查表达式是否为指定名称。
#
#  @param node Candidate AST expression.
#  @param name Expected identifier spelling.
#  @return True only for a matching ast.Name node.
def _name(node, name):
    return isinstance(node, ast.Name) and node.id == name


## Compare an AST expression with a parsed canonical source expression.
## 将 AST 表达式与解析得到的规范源码表达式比较。
#
#  @param left Expression from the analyzed source.
#  @param source Canonical expression text used for structural comparison.
#  @return True when both expressions have the same attribute-free AST shape.
def _same(left, source):
    return ast.dump(left, include_attributes=False) == ast.dump(ast.parse(source, mode='eval').body,
                                                              include_attributes=False)


## Check whether an exception expression can safely format a missing name.
## 检查异常表达式是否能安全地格式化缺失名称。
#
#  @param node Candidate exception argument expression.
#  @param receiver Name of the module-level receiver parameter.
#  @param parameter Name of the requested attribute parameter.
#  @return True for constants and the narrowly supported receiver/name expressions.
def _failure(node, receiver, parameter):
    if isinstance(node, ast.Constant):
        return type(node.value) in (str, int, type(None))
    if _name(node, parameter) or isinstance(node, ast.Attribute) and _name(
            node.value, receiver) and node.attr == '__module__':
        return True
    if isinstance(node, ast.JoinedStr):
        return all(_failure(item, receiver, parameter) for item in node.values)
    if isinstance(node, ast.FormattedValue):
        return (node.format_spec is None and node.conversion in (-1, 97, 114, 115)
                and _failure(node.value, receiver, parameter))
    return False


## Audit functools cache bindings used by source module property dispatch.
## 审计源码模块 property 分派所使用的 functools 缓存绑定。
#
#  @param analyzer Analyzer containing module bodies and import bindings.
#  @return Stability flag and source paths inspected for the premise.
def _cache_namespace(analyzer):
    cached = getattr(analyzer, '_module_getattr_cache_premises', None)
    if cached is not None:
        return cached

    # Cache results only after the whole snapshot scan completes successfully.
    # 仅在完整扫描快照后缓存结果。
    paths, count, stable = set(), 0, 'functools' not in analyzer.module_bodies
    for bodies in analyzer.module_bodies.values():
        for path, body in bodies:
            paths.add(path)
            nodes, parents, aliases = [], {}, {}
            for statement in body:
                for node in ast.walk(statement):
                    count += 1

                    # Bound the snapshot-wide audit of cache imports and uses.
                    # 限制对快照中缓存导入和用法的整体审计规模。
                    if count > 1000000:
                        raise _ClassEffectLimit()
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    nodes.append(node)
                    for child in ast.iter_child_nodes(node):
                        parents[child] = node
                    for fact in import_facts(node):
                        if fact.kind == 'import' and fact.name == 'functools':
                            aliases[fact.python_binding] = 'functools'
                        elif fact.kind == 'from' and fact.module == 'functools' and not fact.level:
                            if fact.name in ('lru_cache', '*'):
                                aliases[fact.python_binding] = 'functools.' + fact.name
            for node in nodes:
                if (isinstance(node, ast.Call) and node.args
                        and isinstance(node.args[0], ast.Constant) and node.args[0].value == 'functools'
                        and (isinstance(node.func, ast.Name) and node.func.id == '__import__'
                             or isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module')):
                    stable = False
                if not isinstance(node, ast.Name) or node.id not in aliases:
                    continue
                current, qualified = node, aliases[node.id]
                if not isinstance(node.ctx, ast.Load) or qualified.endswith('.*'):
                    stable = False
                if qualified == 'functools':
                    current = parents.get(node)
                    if not isinstance(current, ast.Attribute) or current.value is not node:
                        stable = False
                        continue
                    if current.attr.startswith('__') and current.attr.endswith('__'):
                        stable = False
                    qualified += '.' + current.attr
                if qualified == 'functools.lru_cache':
                    use = parents.get(current)
                    if (not isinstance(current.ctx, ast.Load)
                            or not (isinstance(use, ast.Call) and use.func is current
                                or isinstance(use, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                                and current in use.decorator_list)):
                        stable = False
    result = stable, tuple(sorted(paths))
    analyzer._module_getattr_cache_premises = result
    return result


## Prove one name misses a finite source property-based module getattr dispatch.
## 证明某个名称在有限源码 property 模块级 getattr 分派中缺失。
#
#  @param analyzer Fixed source definitions/imports; no module is executed.
#  @param module Package whose missing attribute may trigger a from-import.
#  @param name Exact attribute being requested.
#  @return Conditional missing-name fact, or None for unknown lookup.
def missing(analyzer, module, name):
    if type(name) is not str:
        return None
    bindings = analyzer.import_binding_facts.get(module, [])
    if (len(bindings) != 1 or bindings[0].get('__name__') or bindings[0].get('__builtins__')):
        return None

    # Require one stable module namespace and one source-defined getattr class.
    # 要求模块命名空间唯一且稳定，并且恰有一个源码定义的 getattr 类。
    classes = analyzer._definition_index.find(module, '__getattr__', kind='class')
    if len(classes) != 1:
        return None
    ref, cls = classes[0]
    if (cls.bases or cls.keywords or analyzer.definition_conditions.get(ref)
            or not analyzer._stable_import_name(module + '.__getattr__')
            or len(cls.decorator_list) != 1):
        return None
    factory = analyzer._decorator_definition((ref, cls))
    if factory is None or not isinstance(factory[1], ast.FunctionDef):
        return None
    owner, function = factory
    if '.' in owner.qualname or analyzer.definition_conditions.get(owner):
        return None
    inspected = 0
    for source in (cls, function):
        for _ in ast.walk(source):
            inspected += 1
            if inspected > 2000:
                return None
            if analyzer._analysis_budget is not None:
                analyzer._analysis_budget.checkpoint()
    args = function.args
    positional = args.posonlyargs + args.args
    if (len(positional) != 1 or args.defaults or args.vararg or args.kwarg or args.kwonlyargs
            or positional[0].annotation is not None or function.returns is not None):
        return None
    receiver = positional[0].arg
    body = _body(function)
    if body and isinstance(body[0], ast.Assert):
        if not _same(body[0].test, receiver + '.__name__ == ' + repr(cls.name)) or body[0].msg:
            return None
        body = body[1:]
    if len(body) != 4:
        return None

    # Match the dispatch table, helper instance, cached getter, and return as one fixed shape.
    # 将分派表、辅助对象、缓存 getter 和返回语句匹配为一个固定结构。
    table, instance, getter, returned = body
    if (not isinstance(table, ast.Assign) or len(table.targets) != 1
            or not isinstance(table.targets[0], ast.Name) or not isinstance(table.value, ast.DictComp)
            or not isinstance(instance, ast.Assign) or len(instance.targets) != 1
            or not isinstance(instance.targets[0], ast.Name)
            or not _same(instance.value, receiver + '()')
            or not isinstance(getter, ast.FunctionDef) or not isinstance(returned, ast.Return)
            or not _name(returned.value, getter.name)):
        return None
    mapping, generated = table.targets[0].id, table.value
    if (len(generated.generators) != 1 or generated.generators[0].is_async
            or not isinstance(generated.generators[0].target, ast.Tuple)
            or len(generated.generators[0].target.elts) != 2
            or not all(isinstance(item, ast.Name) for item in generated.generators[0].target.elts)):
        return None
    generator = generated.generators[0]
    key, value = (item.id for item in generator.target.elts)
    if (not _name(generated.key, key) or not _name(generated.value, value)
            or not _same(generator.iter, 'vars(' + receiver + ').items()')
            or len(generator.ifs) != 1
            or not _same(generator.ifs[0], 'isinstance(' + value + ', property)')):
        return None
    parameters = getter.args.posonlyargs + getter.args.args
    if (len(parameters) != 1 or getter.args.defaults or getter.args.kwonlyargs
            or getter.args.vararg or getter.args.kwarg or getter.returns is not None
            or parameters[0].annotation is not None or len(getter.decorator_list) != 1):
        return None
    parameter = parameters[0].arg
    outer = {receiver, mapping, instance.targets[0].id, getter.name, parameter}
    if (len(outer) != 5 or key == value or {key, value} & (outer - {parameter})
            or (outer | {key, value}) & {'vars', 'isinstance', 'property', 'AttributeError'}):
        return None
    decoration = getter.decorator_list[0]
    if (not isinstance(decoration, ast.Call) or len(decoration.args) != 1 or decoration.keywords
            or not isinstance(decoration.args[0], ast.Constant) or decoration.args[0].value is not None
            or not isinstance(decoration.func, (ast.Name, ast.Attribute))):
        return None
    head, dot, rest = ast.unparse(decoration.func).partition('.')
    imported = analyzer.imports.get(owner.module, {}).get(head, '')
    if (imported + (dot + rest if dot else '') != 'functools.lru_cache'
            or 'functools' in analyzer.module_bodies
            or not analyzer._stable_import_name(owner.module + '.' + head)
            or head in analyzer._scope_facts(function).bound
            or any(not analyzer._stable_import_name(source + '.' + alias)
                for source, imports in analyzer.imports.items() for alias, canonical in imports.items()
                if canonical in ('functools', 'functools.lru_cache'))):
        return None
    selected = _body(getter)
    if (len(selected) != 2 or not isinstance(selected[0], ast.If) or selected[0].orelse
            or not _same(selected[0].test, parameter + ' in ' + mapping)
            or not isinstance(selected[1], ast.Raise) or selected[1].cause is not None):
        return None
    if (len(selected[0].body) != 1 or not isinstance(selected[0].body[0], ast.Return)
            or not _same(selected[0].body[0].value,
                         mapping + '[' + parameter + '].__get__(' + instance.targets[0].id + ')')):
        return None
    raised = selected[1].exc
    if (not isinstance(raised, ast.Call) or not _name(raised.func, 'AttributeError')
            or raised.keywords or not all(_failure(arg, receiver, parameter) for arg in raised.args)):
        return None

    # Confirm builtin names and reject class members outside the finite property table.
    # 确认内建名称，并拒绝有限 property 表之外的类成员。
    if not all(analyzer._builtin_name_status(owner, function, builtin) == 'confirmed_builtin'
               for builtin in ('vars', 'isinstance', 'property', 'AttributeError')):
        return None
    property_names = set()
    forbidden = {'__new__', '__init__', '__init_subclass__', '__getattribute__', '__getattr__',
                 '__setattr__', '__slots__', '__class__', '__bases__', '__module__', '__dict__',
                 '__weakref__', '__qualname__', '__name__'}
    for statement in _body(cls):
        if isinstance(statement, ast.Pass):
            continue
        if (not isinstance(statement, ast.Assign) or len(statement.targets) != 1
                or not isinstance(statement.targets[0], ast.Name)
                or statement.targets[0].id in forbidden):
            return None
        expression = statement.value
        if isinstance(expression, ast.Constant):
            property_names.discard(statement.targets[0].id)
            continue
        if (not isinstance(expression, ast.Call) or not _name(expression.func, 'property')
                or len(expression.args) != 1 or expression.keywords
                or not isinstance(expression.args[0], ast.Lambda)):
            return None
        lambda_args = expression.args[0].args
        if (lambda_args.defaults or lambda_args.kwonlyargs or lambda_args.vararg or lambda_args.kwarg
                or 'property' in analyzer._builtin_scope_facts(cls).bound):
            return None
        property_names.add(statement.targets[0].id)
    if name in property_names or len(property_names) > 128:
        return None

    # Return only conditional source evidence after builtin/cache namespace checks pass.
    # 仅在内建和缓存命名空间检查通过后返回条件式源码证据。
    try:
        stable, paths = _stable_builtin_namespace(analyzer, ref,
            ('property', 'vars', 'isinstance', 'AttributeError'))
        cache_stable, cache_paths = _cache_namespace(analyzer)
    except _ClassEffectLimit:
        return None
    if not stable or not cache_stable:
        return None
    return {'kind': 'source_module_getattr_missing', 'status': 'missing_on_dispatch',
        'basis': 'source_snapshot', 'module': module, 'attribute': name,
        'definition': asdict(ref), 'factory': asdict(owner),
        'property_names': sorted(property_names), 'exception': 'AttributeError',
        'runtime_lookup_confirmed': False,
        'source_hashes': {path: analyzer.hashes[path]
                          for path in sorted(set(paths) | set(cache_paths) | {owner.file_path})},
        'assumptions': ['source_snapshot_bindings_hold', 'standard_builtin_namespace_preserved',
            'standard_library_lru_cache_protocol', 'source_getattr_dispatch_table_preserved',
            'no_external_monkeypatch_or_import_hook', 'no_unmodeled_indirect_builtin_mutation']}
