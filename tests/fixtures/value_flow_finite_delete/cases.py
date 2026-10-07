def sink(**kwargs):
    return kwargs


def remove_keys(mapping, keys):
    for key in keys:
        if key in mapping:
            del mapping[key]


def clean(mapping, keys):
    alias = mapping
    for key in keys:
        if key in alias:
            del alias[key]
    return alias


def root(**kwargs):
    remove_keys(kwargs, ('out', 'p'))
    return sink(**kwargs)


def returned(**kwargs):
    keys = ['out', 'p']
    forwarded = clean(kwargs, keys)
    forwarded.pop('unused', None)
    return sink(**kwargs), sink(**forwarded)


def finite(x, y):
    mapping = {'out': x, 'keep': y}
    remove_keys(mapping, ('out', 'missing'))
    return sink(**mapping)


def independent(x, y):
    first, second = {'out': x}, {'out': y}
    remove_keys(first, ('out',))
    remove_keys(second, ('other',))
    return sink(**first), sink(**second)


def unknown_keys(keys, **kwargs):
    remove_keys(kwargs, keys)
    return sink(**kwargs)


def unknown_mapping(mapping):
    remove_keys(mapping, ('out',))
    return mapping


def non_string(**kwargs):
    remove_keys(kwargs, ('out', 1))
    return sink(**kwargs)


def conditional(flag, **kwargs):
    if flag:
        remove_keys(kwargs, ('out',))
    return sink(**kwargs)


def warning(mapping, keys):
    for key in keys:
        if key in mapping:
            warnings.warn(key)
            del mapping[key]


def unknown_call(**kwargs):
    warning(kwargs, ('out',))
    return sink(**kwargs)


def caught(mapping, keys):
    try:
        for key in keys:
            if key in mapping:
                del mapping[key]
    except Exception:
        mapping['out'] = None


def exception_path(**kwargs):
    caught(kwargs, ('out',))
    return sink(**kwargs)


def clear_then_delete(mapping, keys):
    mapping.clear()
    for key in keys:
        if key in mapping:
            del mapping[key]
    return mapping


def cleared(**kwargs):
    result = clear_then_delete(kwargs, ('out',))
    return sink(**result)


def mutated_keys(**kwargs):
    keys = ['out']
    unknown_effect(keys)
    remove_keys(kwargs, keys)
    return sink(**kwargs)


def recursive(mapping, keys):
    recursive(mapping, keys)
    for key in keys:
        if key in mapping:
            del mapping[key]


def recursive_entry(**kwargs):
    recursive(kwargs, ('out',))
    return sink(**kwargs)


def escape_after(mapping):
    unknown_effect(mapping)


def after_unknown(**kwargs):
    remove_keys(kwargs, ('out',))
    escape_after(kwargs)
    return sink(**kwargs)


def clear_keys(mapping, keys):
    keys.clear()
    for key in keys:
        if key in mapping:
            del mapping[key]
    return mapping


def clear_key_alias(mapping, keys, other):
    other.clear()
    for key in keys:
        if key in mapping:
            del mapping[key]
    return mapping


def helper_mutated_keys(**kwargs):
    keys = ['out']
    forwarded = clear_keys(kwargs, keys)
    return sink(**kwargs), sink(**forwarded)


def helper_mutated_key_alias(**kwargs):
    keys = ['out']
    clear_key_alias(kwargs, keys, keys)
    return sink(**kwargs)
