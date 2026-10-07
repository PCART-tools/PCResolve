def fixed(allowed=0):
    return allowed


def sink(**kwargs):
    return kwargs


def helper(values, mapping):
    if not values:
        return mapping
    unknown_effect(mapping)
    return mapping


def clean(values, mapping):
    if not values:
        mapping.pop('before', None)
        alias = mapping
        return alias
    unknown_effect(mapping)
    return mapping


def root(**kwargs):
    mapping = helper((), kwargs)
    mapping.pop('out', None)
    return fixed(**mapping)


def alias_clear(**kwargs):
    empty = ()
    mapping = helper(empty, kwargs)
    mapping.clear()
    return fixed(**kwargs)


def mutated(**kwargs):
    mapping = clean([], kwargs)
    mapping.pop('out', None)
    return fixed(**kwargs), fixed(**mapping)


def finite(x, y):
    mapping = helper((), {'out': x, 'allowed': y})
    mapping.pop('out', None)
    return sink(**mapping)


def unsafe(**kwargs):
    mapping = helper((1,), kwargs)
    mapping.pop('out', None)
    return fixed(**mapping)


def unknown(values, **kwargs):
    mapping = helper(values, kwargs)
    mapping.pop('out', None)
    return fixed(**mapping)


def contexts(**kwargs):
    first = helper((), kwargs)
    second = helper((1,), kwargs)
    second.clear()
    return fixed(**first)


def copied(values, mapping):
    if not values:
        return {**mapping}
    return mapping


def copy_clear(**kwargs):
    copied((), kwargs).clear()
    return fixed(**kwargs)


def rebuilt(values, mapping):
    if not values:
        return {'allowed': mapping.get('allowed')}
    return mapping


def mixed_return(values, mapping):
    if not values:
        return unknown_factory()
    return mapping


def finalizer(values, mapping):
    try:
        if not values:
            return mapping
    finally:
        unknown_effect(mapping)


def unknown_mutation(values, mapping):
    if not values:
        unknown_effect(mapping)
        return mapping
    return mapping


def escaped_values(values, mapping):
    unknown_effect(values)
    if not values:
        return mapping
    return unknown_factory()


def recursive(values, mapping):
    if not values:
        return recursive(values, mapping)
    return mapping


def negative(kind, **kwargs):
    result = kind((), kwargs)
    result.clear()
    return fixed(**kwargs)


def negative_mixed(**kwargs):
    return negative(mixed_return, **kwargs)


def negative_finally(**kwargs):
    return finalizer((), kwargs).clear()


def negative_mutation(**kwargs):
    return unknown_mutation((), kwargs).clear()


def negative_rebuilt(**kwargs):
    return rebuilt((), kwargs).clear()


def negative_escape(**kwargs):
    return escaped_values([], kwargs).clear()


def negative_recursive(**kwargs):
    return recursive((), kwargs).clear()


def changed_sequence(**kwargs):
    values = []
    values.append(1)
    return helper(values, kwargs).clear()


def effectful_guard(values, mapping):
    if unknown_effect(mapping):
        return mapping
    return mapping


def deep_branch(flag, mapping):
    if flag:
        if flag:
            if flag:
                if flag:
                    if flag:
                        if flag:
                            if flag:
                                if flag:
                                    if flag:
                                        return mapping
    return mapping


def budget_branch(**kwargs):
    return deep_branch(True, kwargs).clear()
