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


## Bound a class parameter's direct writes without asserting whole-function effects.
#  @param node Synchronous source helper; descriptor binding is checked by the caller.
#  @param parameter Exactly bound ordinary class parameter.
#  @param builtin Predicate confirming an unshadowed builtin in this source scope.
#  @param protected Predicate identifying additional source references to this class.
#  @param owner Lexical class name used for private attribute mangling, or empty.
#  @param max_nodes Maximum AST nodes inspected in this proof.
#  @param charge Optional callback charging every attempted inspection, including failures.
#  @return ClassAttributeWrites, or None for escaping/reflective/unknown class use.
def class_attribute_writes(node, parameter, builtin, protected, owner='', max_nodes=2000, charge=None):
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
    attributes, evidence = [], []

    def safe(value, aliases):
        if value is None:
            return True
        for item in ast.walk(value):
            if isinstance(item, ast.Name) and (item.id in aliases or protected(item)):
                return False
            if isinstance(item, ast.Attribute) and item.attr == '__dict__':
                return False
            if isinstance(item, ast.Call) and isinstance(item.func, ast.Name) and item.func.id in (
                    'globals', 'locals', 'vars', 'eval', 'exec', 'compile', '__import__'):
                return False
        return True

    def write(name, statement):
        if name == 'mro' or name.startswith('__') and name.endswith('__'):
            return False
        if owner and name.startswith('__'):
            name = '_' + owner.lstrip('_') + name
        if name not in attributes:
            attributes.append(name)
        if statement not in evidence:
            evidence.append(statement)
        return True

    def target(value, aliases, statement):
        return (isinstance(value, ast.Attribute) and isinstance(value.value, ast.Name)
                and value.value.id in aliases and write(value.attr, statement))

    def block(statements, aliases):
        for statement in statements:
            if isinstance(statement, ast.Assign):
                if isinstance(statement.value, ast.Name) and statement.value.id in aliases:
                    if not all(isinstance(item, ast.Name) for item in statement.targets):
                        return False
                    aliases.update(item.id for item in statement.targets)
                    continue
                if not safe(statement.value, aliases):
                    return False
                for item in statement.targets:
                    if isinstance(item, ast.Name):
                        aliases.discard(item.id)
                    elif not target(item, aliases, statement):
                        return False
            elif isinstance(statement, ast.AnnAssign):
                if not safe(statement.annotation, aliases) or not safe(statement.value, aliases):
                    return False
                if isinstance(statement.target, ast.Name):
                    aliases.discard(statement.target.id)
                elif not target(statement.target, aliases, statement):
                    return False
            elif isinstance(statement, ast.Delete):
                if not all(target(item, aliases, statement) for item in statement.targets):
                    return False
            elif isinstance(statement, ast.If):
                if not safe(statement.test, aliases):
                    return False
                left, right = set(aliases), set(aliases)
                if not block(statement.body, left) or not block(statement.orelse, right):
                    return False
                aliases.update(left | right)
            elif isinstance(statement, ast.Expr):
                call = statement.value
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                        and call.func.id in ('setattr', 'delattr') and call.args
                        and isinstance(call.args[0], ast.Name) and call.args[0].id in aliases):
                    count = 3 if call.func.id == 'setattr' else 2
                    if (not builtin(call.func.id) or len(call.args) != count or call.keywords
                            or not isinstance(call.args[1], ast.Constant)
                            or type(call.args[1].value) is not str
                            or not all(safe(arg, aliases) for arg in call.args[2:])
                            or not write(call.args[1].value, statement)):
                        return False
                elif not safe(call, aliases):
                    return False
            elif isinstance(statement, ast.Return):
                if not safe(statement.value, aliases):
                    return False
            elif not isinstance(statement, ast.Pass):
                return False
        return True

    if not block(node.body, {parameter}):
        return None
    return ClassAttributeWrites(tuple(attributes), tuple(evidence), len(nodes))
