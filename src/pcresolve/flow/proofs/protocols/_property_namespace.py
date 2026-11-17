## @package pcresolve.flow.proofs.protocols._property_namespace
#  Model builtin property construction.
#
#
#  Builtin property construction is separate from descriptor access or execution.
#  内置 property 构造与描述符访问或执行分开分析。



import ast
import builtins
from dataclasses import replace

from pcresolve.flow.proofs.protocols.class_attribute_effects import _ClassEffectLimit
from pcresolve.facts.import_facts import import_facts
from pcresolve.facts.scope_facts import statement_scope_facts
from pcresolve.flow.proofs.protocols.syntax_facts import SyntaxLimit

_PROPERTY_NAMESPACE_NODE_LIMIT = 1000000


## Check whether a projection avoids writes and special attributes.
## 检查投影是否避开写入和特殊属性。
#
#  @param node Root expression node.
#  @param parents Node-to-parent mapping.
#  @return True for a supported read-only projection.
def _readonly_projection(node, parents):
    current = parents.get(node)
    if not isinstance(current, ast.Attribute) or current.value is not node:
        return False
    while isinstance(current, (ast.Attribute, ast.Subscript)):
        if (isinstance(current.ctx, (ast.Store, ast.Del))
                or isinstance(current, ast.Attribute)
                and current.attr.startswith('__') and current.attr.endswith('__')):
            return False
        following = parents.get(current)
        if not (isinstance(following, (ast.Attribute, ast.Subscript))
                and following.value is current):
            break
        current = following
    return True


## Check a narrow builtin read of a module object.
## 检查对模块对象的受限内置只读操作。
#
#  @param analyzer Fixed source analysis state.
#  @param owner Source class identity used to construct lookup references.
#  @param module Current module name.
#  @param path Current source path.
#  @param node Module name expression.
#  @param parent Parent AST node.
#  @param parents Node-to-parent mapping.
#  @return True only for a supported confirmed builtin use.
def _readonly_module_use(analyzer, owner, module, path, node, parent, parents):
    if (not isinstance(parent, ast.Call) or not isinstance(parent.func, ast.Name)
            or parent.func.id not in ('dir', 'getattr', 'hasattr')
            or not parent.args or parent.args[0] is not node or parent.keywords):
        return False
    name = parent.func.id
    if len(parent.args) not in {'dir': (1,), 'getattr': (2, 3), 'hasattr': (2,)}[name]:
        return False
    if name == 'getattr' and not isinstance(parents.get(parent), ast.Compare):
        # An arbitrary attribute result could be the mutable namespace itself.
        # 任意属性结果可能就是可变命名空间本身。
        return False
    names, scope, definition_scope = [], None, True
    child, current = parent, parents.get(parent)
    while current is not None:
        if isinstance(current, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            if any(isinstance(target, ast.Name) and target.id == name
                   for generator in current.generators for target in ast.walk(generator.target)):
                return False
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            names.append(getattr(current, 'name', '<lambda>'))
            if scope is None:
                scope = current
                definition_scope = (child is not current.body if isinstance(current, ast.Lambda)
                                    else child not in current.body)
        child, current = current, parents.get(current)
    qualified = '.'.join(reversed(names))
    if isinstance(scope, ast.ClassDef):
        qualified += '.<namespace>'
        definition_scope = False
    ref = type(owner)(module=module, qualname=qualified, file_path=path)
    return analyzer._builtin_name_status(
        ref, scope, name, definition_scope=definition_scope) == 'confirmed_builtin'


## Check indexed source for possible writes or escapes of builtin names.
## 检查已索引源码中内置名称可能发生的写入或逃逸。
#
#  @param analyzer Fixed source analysis state.
#  @param owner Source identity for builtin lookup.
#  @param protected Builtin names requiring stability.
#  @return Stability flag and examined source paths; exhaustion raises _ClassEffectLimit.
def _stable_builtin_namespace(analyzer, owner, protected=('property',)):
    cache = getattr(analyzer, '_property_namespace_premises', None)
    key = tuple(sorted(protected))
    if isinstance(cache, dict) and key in cache:
        return cache[key]
    paths, inspected, stable = set(), 0, 'builtins' not in analyzer.module_bodies
    for module, bodies in analyzer.module_bodies.items():
        for path, body in bodies:
            paths.add(path)
            try:
                syntax = analyzer._syntax_facts(body, _PROPERTY_NAMESPACE_NODE_LIMIT - inspected)
            except SyntaxLimit:
                raise _ClassEffectLimit()
            if syntax is None:
                nodes, parents, imports = [], {}, []
                for statement in body:
                    for node in ast.walk(statement):
                        inspected += 1
                        if inspected > _PROPERTY_NAMESPACE_NODE_LIMIT:
                            raise _ClassEffectLimit()
                        analyzer._analysis_budget.checkpoint()
                        nodes.append(node)
                        for child in ast.iter_child_nodes(node):
                            parents[child] = node
                        imports.extend(import_facts(node))
            else:
                nodes, parents, imports = syntax.nodes, syntax.parents, syntax.imports
                inspected += len(nodes)
            aliases = {fact.python_binding for fact in imports
                       if fact.kind == 'import' and fact.name == 'builtins'}
            for node in nodes:
                if (key != ('property',) and isinstance(node, ast.ImportFrom)
                        and node.level == 0 and node.module == 'builtins'
                        and any(not isinstance(getattr(builtins, alias.name, None), type)
                                for alias in node.names)):
                    # Imported builtin functions expose their module via
                    # __self__; a plain type reference does not grant that alias.
                    stable = False
                if (isinstance(node, ast.ImportFrom) and node.level == 0
                        and node.module == 'builtins'
                        and any(alias.name == '*' or alias.name.startswith('__')
                                and alias.name.endswith('__') for alias in node.names)):
                    stable = False
                if (isinstance(node, ast.Name) and node.id == '__builtins__'
                        or isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant)
                        and node.slice.value == '__builtins__'):
                    stable = False
                if (isinstance(node, ast.Call) and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and node.args[0].value == 'builtins'
                        and (isinstance(node.func, ast.Name)
                             and node.func.id in ('__import__', 'import_module')
                             or isinstance(node.func, ast.Attribute)
                             and node.func.attr == 'import_module')):
                    if not _readonly_projection(node, parents):
                        stable = False
                if not isinstance(node, ast.Name) or node.id not in aliases:
                    continue
                parent = parents.get(node)
                if (not isinstance(node.ctx, ast.Load) or not isinstance(parent, ast.Attribute)
                        or parent.value is not node):
                    if not _readonly_module_use(
                            analyzer, owner, module, path, node, parent, parents):
                        stable = False
                    continue
                first_attribute = parent.attr
                current = parent
                while isinstance(current, (ast.Attribute, ast.Subscript)):
                    if (isinstance(current, ast.Attribute)
                            and current.attr.startswith('__') and current.attr.endswith('__')
                            or (first_attribute in protected
                                or first_attribute.startswith('__')
                                and first_attribute.endswith('__'))
                            and isinstance(current.ctx, (ast.Store, ast.Del))):
                        stable = False
                    following = parents.get(current)
                    if not (isinstance(following, (ast.Attribute, ast.Subscript))
                            and following.value is current):
                        break
                    current = following
    result = stable, tuple(sorted(paths))
    cache = cache if isinstance(cache, dict) else {}
    cache[key] = result
    analyzer._property_namespace_premises = cache
    return result


## Recognize builtin property/getter/setter/deleter construction in one class body.
## 识别类体中内置 property 及 getter、setter、deleter 的构造。
#
#  @param analyzer Fixed source and import/builtin lookup facts.
#  @param owner Exact source class reference.
#  @param member New function whose evaluated defaults/annotations are checked separately.
#  @param shadowed Names already bound in this class's executing namespace.
#  @param properties Local names previously assigned exact builtin property descriptors.
#  @param dependencies Optional set collecting the namespace guard's source files.
#  @return Explicit construction premise, never getter/setter execution evidence.
def property_declaration(analyzer, owner, member, shadowed, properties, dependencies=None):
    if member.name in ('__init__', '__new__') or len(member.decorator_list) != 1:
        return None
    decorator = member.decorator_list[0]
    accessor = (isinstance(decorator, ast.Attribute)
                and isinstance(decorator.value, ast.Name)
                and decorator.value.id in properties
                and decorator.attr in ('getter', 'setter', 'deleter'))
    builtin = False
    if not accessor:
        if not isinstance(decorator, (ast.Name, ast.Attribute)):
            return None
        name = ast.unparse(decorator)
        head, dot, rest = name.partition('.')
        if head in shadowed:
            return None
        ref = replace(owner, qualname=owner.qualname + '.' + member.name, lineno=member.lineno)
        if (name == 'property'
                and analyzer._builtin_name_status(ref, member, name, definition_scope=True)
                == 'confirmed_builtin'):
            builtin = True
        else:
            imported = analyzer.imports.get(owner.module, {}).get(head, '')
            builtin = (imported + (dot + rest if dot else '') == 'builtins.property'
                       and analyzer._stable_import_name(owner.module + '.' + head))
    if not accessor and not builtin:
        return None
    stable, paths = _stable_builtin_namespace(analyzer, owner)
    if not stable:
        return None
    if dependencies is not None:
        dependencies.update(paths)
    return 'builtin_property_namespace_construction'


## Prove direct native property construction from preceding plain class functions.
## 证明由之前的普通类函数直接构造原生 property。
#
#  @param analyzer Source/import and builtin binding machinery.
#  @param owner Exact class declaration identity.
#  @param cls Class whose statement order supplies the accessors.
#  @param member Property assignment currently being evaluated.
#  @param shadowed Names already bound in this executing namespace.
#  @param dependencies Optional set collecting the namespace guard's source files.
#  @return Construction premise, without invoking any accessor or descriptor.
def property_assignment(analyzer, owner, cls, member, shadowed, dependencies=None):
    if not isinstance(member, (ast.Assign, ast.AnnAssign)):
        return None
    expression = member.value
    if (not isinstance(expression, ast.Call) or not isinstance(expression.func, ast.Name)
            or expression.func.id != 'property' or 'property' in shadowed
            or not 1 <= len(expression.args) <= 4
            or any(keyword.arg != 'doc' for keyword in expression.keywords)
            or len(expression.keywords) > 1 or len(expression.args) == 4 and expression.keywords):
        return None
    # Class-body lookup includes prior class locals, unlike an ordinary method.
    # 类体名称查找包含此前的类局部绑定。
    ref = replace(owner, qualname=owner.qualname + '.<namespace>')
    if analyzer._builtin_name_status(ref, cls, 'property') != 'confirmed_builtin':
        return None
    prior = []
    for statement in cls.body:
        if statement is member:
            break
        prior.append(statement)
    for expression_arg in expression.args[:3]:
        if isinstance(expression_arg, ast.Constant) and expression_arg.value is None:
            continue
        if not isinstance(expression_arg, ast.Name):
            return None
        matches = [statement for statement in prior
                   if expression_arg.id in statement_scope_facts([statement]).bound]
        if (len(matches) != 1 or not isinstance(matches[0], (ast.FunctionDef, ast.AsyncFunctionDef))
                or matches[0].name != expression_arg.id or matches[0].decorator_list):
            return None
    docs = expression.args[3:] + [keyword.value for keyword in expression.keywords]
    if any(not isinstance(value, ast.Constant) or type(value.value) not in (str, type(None))
           for value in docs):
        return None
    stable, paths = _stable_builtin_namespace(analyzer, owner)
    if not stable:
        return None
    if dependencies is not None:
        dependencies.update(paths)
    return 'builtin_property_namespace_construction'
