## @package pcresolve.effect_facts
#  Owner-neutral builtin-container and straight-line function effect facts.

import ast
from dataclasses import dataclass


## Exact supported behavior of one builtin container method call.
@dataclass(frozen=True)
class ContainerMethodEffect:
    ## Canonical operation name.
    operation: str
    ## Formal names for positional arguments.
    parameters: tuple
    ## Whether the operation changes the receiver.
    mutates_receiver: bool

    def __post_init__(self):
        object.__setattr__(self, 'parameters', tuple(self.parameters))


## One exact write in a complete straight-line function summary.
@dataclass(frozen=True)
class FunctionEffect:
    ## Canonical effect kind.
    kind: str
    ## Receiver parameter or nonlocal binding name.
    target: str
    ## Value parameter or capture name, when applicable.
    source: object
    ## AST statement providing source evidence.
    statement: object


## Match a builtin container method by receiver shapes and positional arity.
#  Keyword and expansion uncertainty remains an adapter policy.
#  @param method Attribute method name.
#  @param receiver_shapes Iterable of proven builtin container kinds.
#  @param positional_count Number of syntactic positional arguments.
#  @return ContainerMethodEffect or None when no exact contract is supported.
def container_method_effect(method, receiver_shapes, positional_count):
    shapes = frozenset(receiver_shapes)
    if method == 'append' and shapes == frozenset(('list',)):
        if positional_count == 1:
            return ContainerMethodEffect('append', ('object',), True)
        return None
    if method == 'clear' and shapes and shapes <= frozenset(
            ('list', 'set', 'dict')):
        if positional_count == 0:
            return ContainerMethodEffect('clear', (), True)
        return None
    if method == 'get' and shapes == frozenset(('dict',)):
        if positional_count in (1, 2):
            return ContainerMethodEffect('get', ('key', 'default'), False)
        return None
    if method == 'pop' and shapes == frozenset(('list',)):
        if positional_count in (0, 1):
            return ContainerMethodEffect('pop', ('index',), True)
        return None
    return None


## Determine whether a body yields without entering nested definitions.
#  @param node Root function, lambda, or expression AST.
#  @return True when the root execution contains Yield or YieldFrom.
def contains_yield(node):
    found = False

    def visit(item):
        nonlocal found
        if found:
            return
        if item is not node and isinstance(
                item, (ast.FunctionDef, ast.AsyncFunctionDef,
                       ast.ClassDef, ast.Lambda)):
            return
        if isinstance(item, (ast.Yield, ast.YieldFrom)):
            found = True
            return
        for child in ast.iter_child_nodes(item):
            visit(child)

    visit(node)
    return found


## Extract all effects from a supported straight-line function body.
#  A partial summary is never returned: unsupported statements and generators
#  produce None so callers do not apply an incomplete set of writes.
#  @param node Candidate function definition.
#  @return FunctionEffect tuple, or None when the whole body is unsupported.
def function_effects(node):
    if not isinstance(node, ast.FunctionDef) or contains_yield(node):
        return None
    body = [statement for statement in node.body
            if not (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str))]
    nonlocal_names = {
        name for statement in body if isinstance(statement, ast.Nonlocal)
        for name in statement.names}
    effects = []
    for statement in body:
        if isinstance(statement, ast.Nonlocal):
            continue
        if (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Attribute)
                and isinstance(statement.value.func.value, ast.Name)
                and not statement.value.keywords):
            call = statement.value
            target = call.func.value.id
            if (call.func.attr == 'append' and len(call.args) == 1
                    and isinstance(call.args[0], ast.Name)):
                effects.append(FunctionEffect(
                    'container_append', target, call.args[0].id, statement))
                continue
            if call.func.attr == 'clear' and not call.args:
                effects.append(FunctionEffect(
                    'container_clear', target, None, statement))
                continue
        if (isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id in nonlocal_names
                and isinstance(statement.value, ast.Name)):
            effects.append(FunctionEffect(
                'nonlocal_write', statement.targets[0].id,
                statement.value.id, statement))
            continue
        return None
    return tuple(effects)
