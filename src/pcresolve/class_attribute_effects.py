## @package pcresolve.class_attribute_effects
#  Bounded attribute write sets for one explicitly bound source class object.

import ast
from dataclasses import dataclass


class _ClassEffectLimit(RuntimeError):
    pass


## A partial effect: only the attributes of the protected class are bounded.
@dataclass(frozen=True)
class ClassAttributeWrites:
    ## Possible written/deleted attribute names, with source private-name mangling.
    attributes: tuple
    ## Source statements establishing those operations.
    evidence: tuple
    ## Inspected AST size, charged to the query's shared effect budget.
    nodes: int
    ## Source metadata reads whose entry literals participated in this proof.
    metadata_evidence: tuple = ()


## Bound a class parameter's direct writes without asserting whole-function effects.
#  @param node Synchronous source helper; descriptor binding is checked by the caller.
#  @param parameter Exactly bound ordinary class parameter.
#  @param builtin Predicate confirming an unshadowed builtin in this source scope.
#  @param protected Predicate identifying additional source references to this class.
#  @param owner Lexical class name used for private attribute mangling, or empty.
#  @param max_nodes Maximum AST nodes inspected in this proof.
#  @param charge Optional callback charging every attempted inspection, including failures.
#  @param string_literals Exact incoming ordinary string arguments, without assumed defaults.
#  @param class_name Optional guarded provider for a protected class's entry name.
#  @return ClassAttributeWrites, or None for escaping/reflective/unknown class use.
def class_attribute_writes(node, parameter, builtin, protected, owner='', max_nodes=2000,
                           charge=None, string_literals=None, class_name=None):
    if not isinstance(node, ast.FunctionDef):
        return None
    nodes = []
    for item in ast.walk(node):
        if len(nodes) >= max_nodes:
            if charge is not None:
                charge(len(nodes))
            raise _ClassEffectLimit()
        nodes.append(item)
    if charge is not None:
        charge(len(nodes))
    if any(isinstance(item, (ast.Global, ast.Nonlocal, ast.Yield, ast.YieldFrom,
                             ast.Await, ast.NamedExpr)) for item in nodes):
        return None
    attributes, evidence, metadata_evidence = [], [], []

    def attribute_name(name):
        private_owner = owner.lstrip('_')
        if private_owner and name.startswith('__') and not name.endswith('__'):
            return '_' + private_owner + name
        return name

    def metadata_literal(value, aliases):
        if (class_name is not None and isinstance(value, ast.Attribute)
                and isinstance(value.ctx, ast.Load) and value.attr == '__name__'
                and isinstance(value.value, ast.Name) and value.value.id in aliases):
            name = class_name(value)
            if type(name) is str:
                if value not in metadata_evidence:
                    metadata_evidence.append(value)
                return name
        return None

    def literal_name(value, names, aliases, depth=0):
        if depth > 64:
            raise _ClassEffectLimit()
        if isinstance(value, ast.Constant) and type(value.value) is str:
            result = value.value
        elif isinstance(value, ast.Name):
            result = names.get(value.id)
        elif isinstance(value, ast.Attribute):
            result = metadata_literal(value, aliases)
        elif isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):
            left, right = (literal_name(value.left, names, aliases, depth + 1),
                           literal_name(value.right, names, aliases, depth + 1))
            result = left + right if left is not None and right is not None else None
        else:
            result = None
        return result if result is not None and len(result) <= 2000 else None

    def literal_payload(value):
        # literal_eval also accepts set(), whose source spelling may be shadowed.
        if value is None or any(isinstance(item, ast.Call) for item in ast.walk(value)):
            return False
        try:
            ast.literal_eval(value)
            return True
        except (ValueError, TypeError, RecursionError):
            return False

    def safe(value, aliases, names, plain, depth=0):
        if depth > 64:
            raise _ClassEffectLimit()
        if value is None:
            return True
        if isinstance(value, (ast.Lambda, ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)):
            if any(isinstance(item, ast.Name) and (item.id in aliases or protected(item))
                   for item in ast.walk(value)):
                return False
        if isinstance(value, ast.Name):
            return value.id not in aliases and (value.id in names or not protected(value))
        if isinstance(value, ast.Attribute):
            if value.attr == '__dict__':
                return False
            if isinstance(value.value, ast.Name) and value.value.id in aliases:
                if metadata_literal(value, aliases) is not None:
                    return True
                if not isinstance(value.ctx, ast.Load) or attribute_name(value.attr) not in plain:
                    return False
                if value not in evidence:
                    evidence.append(value)
                return True
        if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
            name = value.func.id
            if name in ('getattr', 'hasattr') and value.args and isinstance(
                    value.args[0], ast.Name) and value.args[0].id in aliases:
                if (not builtin(name) or value.keywords or len(value.args) not in (
                        (2, 3) if name == 'getattr' else (2,))
                        or literal_name(value.args[1], names, aliases) not in plain
                        or not all(safe(arg, aliases, names, plain, depth + 1)
                                   for arg in value.args[2:])):
                    return False
                if value not in evidence:
                    evidence.append(value)
                return True
            if name in (
                    'globals', 'locals', 'vars', 'eval', 'exec', 'compile', '__import__'):
                return False
        return all(safe(item, aliases, names, plain, depth + 1)
                   for item in ast.iter_child_nodes(value))

    def write(name, statement):
        if name == 'mro' or name.startswith('__') and name.endswith('__'):
            return False
        if name not in attributes:
            attributes.append(name)
        if statement not in evidence:
            evidence.append(statement)
        return True

    def target(value, aliases, statement, plain, payload=None):
        if (not isinstance(value, ast.Attribute) or not isinstance(value.value, ast.Name)
                or value.value.id not in aliases):
            return False
        name = attribute_name(value.attr)
        if not write(name, statement):
            return False
        plain.discard(name)
        if literal_payload(payload):
            plain.add(name)
        return True

    def block(statements, aliases, names, plain):
        for statement in statements:
            if isinstance(statement, ast.Assign):
                if isinstance(statement.value, ast.Name) and statement.value.id in aliases:
                    if not all(isinstance(item, ast.Name) for item in statement.targets):
                        return False
                    aliases.update(item.id for item in statement.targets)
                    for item in statement.targets:
                        names.pop(item.id, None)
                    continue
                if not safe(statement.value, aliases, names, plain):
                    return False
                name = literal_name(statement.value, names, aliases)
                for item in statement.targets:
                    if isinstance(item, ast.Name):
                        aliases.discard(item.id)
                        names.pop(item.id, None)
                        if name is not None:
                            names[item.id] = name
                    elif not target(item, aliases, statement, plain, statement.value):
                        return False
            elif isinstance(statement, ast.AnnAssign):
                if not safe(statement.annotation, aliases, names, plain) or not safe(
                        statement.value, aliases, names, plain):
                    return False
                if isinstance(statement.target, ast.Name):
                    aliases.discard(statement.target.id)
                    name = literal_name(statement.value, names, aliases)
                    names.pop(statement.target.id, None)
                    if name is not None:
                        names[statement.target.id] = name
                elif not target(statement.target, aliases, statement, plain, statement.value):
                    return False
            elif isinstance(statement, ast.Delete):
                if not all(target(item, aliases, statement, plain) for item in statement.targets):
                    return False
            elif isinstance(statement, ast.If):
                if not safe(statement.test, aliases, names, plain):
                    return False
                left, right = set(aliases), set(aliases)
                left_names, right_names = dict(names), dict(names)
                left_plain, right_plain = set(plain), set(plain)
                if not block(statement.body, left, left_names, left_plain) or not block(
                        statement.orelse, right, right_names, right_plain):
                    return False
                aliases.update(left | right)
                names.clear()
                names.update({name: value for name, value in left_names.items()
                              if right_names.get(name) == value})
                plain.clear()
                plain.update(left_plain & right_plain)
            elif isinstance(statement, ast.Expr):
                call = statement.value
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                        and call.func.id in ('setattr', 'delattr') and call.args
                        and isinstance(call.args[0], ast.Name) and call.args[0].id in aliases):
                    count = 3 if call.func.id == 'setattr' else 2
                    name = literal_name(call.args[1], names, aliases) if len(call.args) >= 2 else None
                    if (not builtin(call.func.id) or len(call.args) != count or call.keywords
                            or name is None
                            or not all(safe(arg, aliases, names, plain) for arg in call.args[2:])
                            or not write(name, statement)):
                        return False
                    plain.discard(name)
                    if call.func.id == 'setattr' and literal_payload(call.args[2]):
                        plain.add(name)
                elif not safe(call, aliases, names, plain):
                    return False
            elif isinstance(statement, ast.Return):
                if not safe(statement.value, aliases, names, plain):
                    return False
            elif not isinstance(statement, ast.Pass):
                return False
        return True

    ordinary = {arg.arg for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
    names = {name: value for name, value in (string_literals or {}).items()
             if name in ordinary and name != parameter and type(value) is str and len(value) <= 2000}
    if not block(node.body, {parameter}, names, set()):
        return None
    return ClassAttributeWrites(tuple(attributes), tuple(evidence), len(nodes), tuple(metadata_evidence))
