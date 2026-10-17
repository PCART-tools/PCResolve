## @package pcresolve._property_namespace
#  Builtin property construction is separate from descriptor access or execution.

import ast
from dataclasses import replace

from .class_attribute_effects import _ClassEffectLimit
from .import_facts import import_facts

_PROPERTY_NAMESPACE_NODE_LIMIT = 1000000


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


def _stable_builtin_namespace(analyzer, owner):
    cached = getattr(analyzer, '_property_namespace_premises', None)
    if cached is not None:
        return cached
    paths, inspected, stable = set(), 0, 'builtins' not in analyzer.module_bodies
    for module, bodies in analyzer.module_bodies.items():
        for path, body in bodies:
            paths.add(path)
            nodes, parents = [], {}
            for statement in body:
                for node in ast.walk(statement):
                    inspected += 1
                    if inspected > _PROPERTY_NAMESPACE_NODE_LIMIT:
                        raise _ClassEffectLimit()
                    if analyzer._analysis_budget is not None:
                        analyzer._analysis_budget.checkpoint()
                    nodes.append(node)
                    for child in ast.iter_child_nodes(node):
                        parents[child] = node
            aliases = {fact.python_binding for node in nodes for fact in import_facts(node)
                       if fact.kind == 'import' and fact.name == 'builtins'}
            for node in nodes:
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
                            or (first_attribute == 'property'
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
    analyzer._property_namespace_premises = result
    return result


## Recognize builtin property/getter/setter/deleter construction in one class body.
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
