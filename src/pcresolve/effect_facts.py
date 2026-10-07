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
    ## Required builtin receiver shape; None for the older protocol summaries.
    receiver_shape: object = None
    ## Constant element path, empty for whole-container effects.
    element_path: tuple = ()
    ## Possible exception before normal completion, when known.
    may_raise: object = None
    ## Finite-key iteration syntax; concrete sequence is supplied by the adapter.
    sequence_loop: object = None
    ## Membership guard protecting an element deletion.
    membership_test: object = None


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
    if method == 'pop' and shapes == frozenset(('dict',)):
        if positional_count in (1, 2):
            return ContainerMethodEffect('mapping_pop', ('key', 'default'), True)
        return None
    if method == 'update' and shapes == frozenset(('dict',)):
        if positional_count in (0, 1):
            return ContainerMethodEffect('mapping_update', ('other',), True)
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
#  Ordinary-parameter aliases and constant-string-key pop/delete facts retain
#  receiver shape prerequisites, not an inferred type for generic parameters.
#  Effects describe normal completion; required-key removals may raise KeyError.
#  @param node Candidate function definition.
#  @return FunctionEffect tuple, or None when the whole body is unsupported.
def function_effects(node):
    if not isinstance(node, ast.FunctionDef) or contains_yield(node):
        return None
    body = [statement for statement in node.body
            if not (isinstance(statement, ast.Expr)
                    and isinstance(statement.value, ast.Constant)
                    and isinstance(statement.value.value, str))]
    if any(isinstance(statement, ast.Global) for statement in body):
        return None
    nonlocal_names = {
        name for statement in body if isinstance(statement, ast.Nonlocal)
        for name in statement.names}
    ordinary = node.args.posonlyargs + node.args.args + node.args.kwonlyargs
    aliases = {argument.arg: argument.arg for argument in ordinary}

    def mapping_pop(value, statement):
        if (not isinstance(value, ast.Call)
                or not isinstance(value.func, ast.Attribute)
                or value.func.attr != 'pop'
                or not isinstance(value.func.value, ast.Name)
                or value.func.value.id not in aliases
                or value.keywords or len(value.args) not in (1, 2)
                or not isinstance(value.args[0], ast.Constant)
                or not isinstance(value.args[0].value, str)
                or (len(value.args) == 2
                    and not isinstance(value.args[1], ast.Constant))):
            return None
        return FunctionEffect('mapping_pop', aliases[value.func.value.id], None,
                              statement, 'dict', (value.args[0].value,),
                              'KeyError' if len(value.args) == 1 else None)

    effects = []
    for statement in body:
        if isinstance(statement, (ast.Nonlocal, ast.Pass)):
            continue
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and statement.targets[0].id not in nonlocal_names
                and isinstance(statement.value, ast.Name)
                and statement.value.id in aliases):
            aliases[statement.targets[0].id] = aliases[statement.value.id]
            continue
        if (isinstance(statement, ast.For) and not statement.orelse
                and isinstance(statement.target, ast.Name)
                and isinstance(statement.iter, ast.Name) and statement.iter.id in aliases
                and statement.target.id not in aliases and len(statement.body) == 1
                and isinstance(statement.body[0], ast.If)):
            branch = statement.body[0]
            test = branch.test
            if (not branch.orelse and len(branch.body) == 1
                    and isinstance(branch.body[0], ast.Delete)
                    and len(branch.body[0].targets) == 1
                    and isinstance(test, ast.Compare) and len(test.ops) == 1
                    and isinstance(test.ops[0], ast.In) and len(test.comparators) == 1
                    and isinstance(test.left, ast.Name) and test.left.id == statement.target.id
                    and isinstance(test.comparators[0], ast.Name)
                    and test.comparators[0].id in aliases):
                target = branch.body[0].targets[0]
                if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                        and target.value.id == test.comparators[0].id
                        and isinstance(target.slice, ast.Name)
                        and target.slice.id == statement.target.id):
                    effects.append(FunctionEffect('mapping_delete_keys',
                        aliases[target.value.id], aliases[statement.iter.id],
                        branch.body[0], 'dict', (), None, statement, test))
                    continue
        if isinstance(statement, (ast.Expr, ast.Return)):
            effect = mapping_pop(statement.value, statement)
            if effect is not None:
                effects.append(effect)
                if isinstance(statement, ast.Return):
                    return tuple(effects)
                continue
        if isinstance(statement, ast.Delete) and len(statement.targets) == 1:
            target = statement.targets[0]
            if (isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in aliases
                    and isinstance(target.slice, ast.Constant)
                    and isinstance(target.slice.value, str)):
                effects.append(FunctionEffect(
                    'mapping_delete', aliases[target.value.id], None,
                    statement, 'dict', (target.slice.value,), 'KeyError'))
                continue
        if isinstance(statement, ast.Return):
            if (statement.value is None or isinstance(statement.value, ast.Constant)
                    or isinstance(statement.value, ast.Name)
                    and statement.value.id in aliases):
                return tuple(effects)
            return None
        if (isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Attribute)
                and isinstance(statement.value.func.value, ast.Name)
                and not statement.value.keywords):
            call = statement.value
            target = aliases.get(call.func.value.id, call.func.value.id)
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


## Extract guarded deletion sites without claiming a complete effect summary.
#  Additional statements may throw, mutate or escape; these facts describe
#  conditional source operations only, never normal-return postconditions.
#  @param node Source function with ordinary mapping and sequence parameters.
#  @return Symbolic sites; None of them authorizes a strong update by itself.
def finite_key_delete_sites(node):
    if not isinstance(node, ast.FunctionDef) or contains_yield(node):
        return ()
    aliases = {argument.arg: argument.arg for argument in node.args.posonlyargs
               + node.args.args + node.args.kwonlyargs}
    sites = []
    for statement in node.body:
        if (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and isinstance(statement.value, ast.Name) and statement.value.id in aliases):
            aliases[statement.targets[0].id] = aliases[statement.value.id]
            continue
        if (not isinstance(statement, ast.For) or statement.orelse
                or not isinstance(statement.iter, ast.Name) or statement.iter.id not in aliases
                or not isinstance(statement.target, ast.Name) or statement.target.id in aliases
                or len(statement.body) != 1 or not isinstance(statement.body[0], ast.If)):
            break
        branch = statement.body[0]
        test = branch.test
        if (branch.orelse or not isinstance(test, ast.Compare) or len(test.ops) != 1
                or not isinstance(test.ops[0], ast.In) or len(test.comparators) != 1
                or not isinstance(test.left, ast.Name) or test.left.id != statement.target.id
                or not isinstance(test.comparators[0], ast.Name)
                or test.comparators[0].id not in aliases):
            break
        receiver, key = test.comparators[0].id, statement.target.id
        if any(isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del))
               and child.id in (receiver, key) for body in branch.body for child in ast.walk(body)):
            break
        for body in branch.body:
            if isinstance(body, ast.Delete) and len(body.targets) == 1:
                target = body.targets[0]
                if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                        and target.value.id == receiver and isinstance(target.slice, ast.Name)
                        and target.slice.id == key):
                    sites.append(FunctionEffect('mapping_delete_keys', aliases[receiver],
                        aliases[statement.iter.id], body, 'dict', (), None, statement, test))
    return tuple(sites)
