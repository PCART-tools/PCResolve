## @package pcresolve.mapping_remainders
#  Bounded source proofs for the unchanged part of an unescaped builtin dict.

import ast
from dataclasses import dataclass


class _ProofLimit(RuntimeError):
    pass


## An unchanged-key projection and one consistent normal-return alias route.
@dataclass(frozen=True)
class MappingRemainder:
    ## Keys possibly written or removed; other input entries remain unchanged.
    excluded_keys: tuple
    ## None for a non-alias return; () for the dict itself; (i,) for a tuple slot.
    return_path: object
    ## Fixed tuple size, or zero for a direct/non-alias return.
    return_size: int
    ## Source statements witnessing the bounded operations and returns.
    evidence: tuple


## Prove a finite-key remainder, without claiming complete values for those keys.
#  The caller must establish a fresh, unescaped builtin dict and distinct inputs.
#  Unsupported accesses, reflection, escaping calls and arbitrary iteration fail.
#  @param node Undecorated synchronous source function.
#  @param parameter Protected ordinary dict parameter.
#  @param sequences Finite literal string sequences supplied at this call.
#  @param builtin Predicate establishing a builtin spelling in this source scope.
#  @param max_nodes Maximum source AST nodes inspected.
#  @return MappingRemainder or None; raised paths do not become return witnesses.
def mapping_remainder(node, parameter, sequences, builtin, max_nodes=2000):
    if (not isinstance(node, ast.FunctionDef) or node.decorator_list
            or sum(1 for _ in ast.walk(node)) > max_nodes):
        return None
    ordinary = {arg.arg for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs}
    if parameter not in ordinary:
        return None
    if any(isinstance(n, (ast.Global, ast.Nonlocal, ast.Try, ast.With, ast.While,
                          ast.AsyncFor, ast.AsyncWith, ast.Yield, ast.YieldFrom,
                          ast.AugAssign, ast.NamedExpr, ast.Lambda, ast.ClassDef))
           or isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not node
           or isinstance(n, ast.Name) and n.id in ('locals', 'vars', 'eval', 'exec',
                                                  'globals', '__builtins__')
           or isinstance(n, ast.Attribute) and n.attr in ('_getframe', 'currentframe', 'f_locals')
           for n in ast.walk(node)):
        return None
    touched, evidence, returns = set(), [], []
    states = 0

    def finite(value, seq, keys):
        if isinstance(value, ast.Name):
            return keys.get(value.id)
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return frozenset((value.value,))
        return None

    def sequence(value, seq):
        if isinstance(value, ast.Name):
            return seq.get(value.id)
        if isinstance(value, (ast.Tuple, ast.List)) and len(value.elts) <= 64 and all(
                isinstance(x, ast.Constant) and isinstance(x.value, str) for x in value.elts):
            return frozenset(x.value for x in value.elts)
        return None

    def references(value, aliases):
        return any(isinstance(n, ast.Name) and n.id in aliases for n in ast.walk(value))

    def expression(value, aliases, seq, keys):
        if value is None:
            return True
        if isinstance(value, ast.Call):
            if isinstance(value.func, ast.Attribute) and isinstance(value.func.value, ast.Name) \
                    and value.func.value.id in aliases:
                method = value.func.attr
                if (method not in ('pop', 'get') or value.keywords
                        or len(value.args) not in (1, 2)
                        or len(value.args) == 2 and not isinstance(value.args[1], ast.Constant)):
                    return False
                bound = finite(value.args[0], seq, keys)
                if bound is None:
                    return False
                if method == 'pop':
                    touched.update(bound)
                    evidence.append(value)
                return True
            if references(value, aliases):
                return False
            # An unknown call may mutate a finite sequence supplied to it.
            names = {n.id for n in ast.walk(value) if isinstance(n, ast.Name)}
            for name in names & seq.keys():
                seq.pop(name, None)
            return True
        if isinstance(value, ast.Name):
            return value.id not in aliases
        if isinstance(value, ast.Subscript) and isinstance(value.value, ast.Name) \
                and value.value.id in aliases:
            return finite(value.slice, seq, keys) is not None
        if isinstance(value, ast.Compare) and len(value.ops) == 1 and isinstance(
                value.ops[0], (ast.In, ast.NotIn)) and len(value.comparators) == 1 \
                and isinstance(value.comparators[0], ast.Name) \
                and value.comparators[0].id in aliases:
            return finite(value.left, seq, keys) is not None
        return all(expression(child, aliases, seq, keys) for child in ast.iter_child_nodes(value))

    def block(body, aliases, seq, keys):
        nonlocal states
        for statement in body:
            states += 1
            if states > 256 or len(touched) > 64:
                raise _ProofLimit('mapping remainder proof budget exhausted')
            if isinstance(statement, ast.Pass):
                continue
            if isinstance(statement, ast.Return):
                value = statement.value
                path, size = None, 0
                if isinstance(value, ast.Name) and value.id in aliases:
                    path = ()
                elif isinstance(value, ast.Tuple) and len(value.elts) <= 64:
                    slots = [i for i, item in enumerate(value.elts)
                             if isinstance(item, ast.Name) and item.id in aliases]
                    if len(slots) == 1 and all(i in slots or expression(item, aliases, seq, keys)
                                               for i, item in enumerate(value.elts)):
                        path, size = (slots[0],), len(value.elts)
                    elif references(value, aliases):
                        return None
                elif not expression(value, aliases, seq, keys):
                    return None
                returns.append((path, size))
                evidence.append(statement)
                return False
            if isinstance(statement, ast.Raise):
                return False if expression(statement.exc, aliases, seq, keys) else None
            if isinstance(statement, ast.If):
                if not expression(statement.test, aliases, seq, keys):
                    return None
                left_a, right_a = set(aliases), set(aliases)
                left_s, right_s = dict(seq), dict(seq)
                left = block(statement.body, left_a, left_s, dict(keys))
                right = block(statement.orelse, right_a, right_s, dict(keys))
                if left is None or right is None or left and right and left_a != right_a:
                    return None
                if not left and not right:
                    return False
                aliases.clear()
                aliases.update(left_a if left else right_a)
                seq.clear()
                seq.update({name: left_s[name] | right_s[name] for name in left_s.keys() & right_s.keys()}
                           if left and right else left_s if left else right_s)
                continue
            if isinstance(statement, ast.For):
                target, iterable = statement.target, statement.iter
                key_name = target.id if isinstance(target, ast.Name) else None
                bound = sequence(iterable, seq)
                if (isinstance(iterable, ast.Call) and isinstance(iterable.func, ast.Name)
                        and iterable.func.id == 'zip' and builtin('zip') and not iterable.keywords
                        and len(iterable.args) == 2 and isinstance(target, ast.Tuple)
                        and len(target.elts) == 2 and all(isinstance(x, ast.Name) for x in target.elts)
                        and not references(iterable, aliases)):
                    key_name = target.elts[0].id
                    bound = sequence(iterable.args[0], seq)
                if (bound is None or key_name is None or statement.orelse
                        or any(isinstance(n, ast.Name) and n.id in aliases
                               for n in ast.walk(target))
                        or key_name in aliases or key_name in seq
                        or any(isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))
                               and n.id == key_name for s in statement.body for n in ast.walk(s))
                        or any(isinstance(n, ast.Call) and any(
                               isinstance(v, ast.Name) and v.id in seq for v in ast.walk(n))
                               for s in statement.body for n in ast.walk(s))
                        or any(isinstance(n, ast.Return) for s in statement.body for n in ast.walk(s))
                        or any(isinstance(n, (ast.Break, ast.Continue)) for n in ast.walk(statement))):
                    return None
                old_aliases = set(aliases)
                status = block(statement.body, aliases, dict(seq), dict(keys, **{key_name: bound}))
                if status is None or aliases != old_aliases:
                    return None
                evidence.append(statement)
                continue
            if isinstance(statement, (ast.Assign, ast.AnnAssign, ast.Delete)):
                targets = (statement.targets if isinstance(statement, (ast.Assign, ast.Delete))
                           else [statement.target])
                value = getattr(statement, 'value', None)
                if len(targets) == 1 and isinstance(targets[0], ast.Name):
                    name = targets[0].id
                    if isinstance(value, ast.Name) and value.id in aliases:
                        aliases.add(name)
                        evidence.append(statement)
                    else:
                        if (name in aliases or name in keys
                                or isinstance(value, ast.Name) and value.id in seq
                                or not expression(value, aliases, seq, keys)):
                            return None
                        bound = sequence(value, seq)
                        seq.pop(name, None)
                        if bound is not None:
                            seq[name] = bound
                    continue
                for target in targets:
                    if (not isinstance(target, ast.Subscript) or not isinstance(target.value, ast.Name)
                            or target.value.id not in aliases):
                        return None
                    bound = finite(target.slice, seq, keys)
                    if bound is None or not expression(value, aliases, seq, keys):
                        return None
                    touched.update(bound)
                    evidence.append(statement)
                continue
            if isinstance(statement, ast.Expr) and expression(statement.value, aliases, seq, keys):
                continue
            return None
        return True

    active = block(node.body, {parameter}, dict(sequences), {})
    if len(touched) > 64:
        raise _ProofLimit('mapping remainder key budget exhausted')
    if active is None:
        return None
    if active:
        returns.append((None, 0))
    if not returns or len(set(returns)) != 1:
        return None
    path, size = returns[0]
    return MappingRemainder(tuple(sorted(touched)), path, size, tuple(evidence))
