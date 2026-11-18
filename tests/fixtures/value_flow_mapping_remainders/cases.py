def fixed(allowed=0):
    return allowed


def normalize(values, mapping):
    if not values:
        return mapping
    names = ['p', 'w', 'V', 'VI']
    notify(len(values))
    for name, value in zip(names, values):
        if name in mapping:
            raise TypeError('duplicate')
        mapping[name] = value
    return mapping


def filter_keys(mapping, keys):
    for key in keys:
        if key in mapping:
            del mapping[key]
            notify(key)


def packed(mapping):
    notify('metadata')
    mapping.pop('before', None)
    return 0, mapping


def root(*args, **kwargs):
    result = normalize(args, kwargs)
    result.pop('out', None)
    filter_keys(result, ['p', 'w'])
    return fixed(**result)


def tuple_root(**kwargs):
    _, result = packed(kwargs)
    result.pop('out', None)
    return fixed(**result)


def tuple_other(**kwargs):
    result, _ = packed(kwargs)
    return fixed(**result)


def cleared(mapping):
    notify('metadata')
    mapping.clear()
    return mapping


def rebuilt(mapping):
    notify('metadata')
    mapping = {'allowed': mapping.get('allowed')}
    return mapping


def changed(mapping):
    notify(mapping)
    return mapping


def rebound_key(mapping, keys):
    for key in keys:
        key = unknown
        del mapping[key]
    return mapping


def growing_keys(mapping, keys):
    for key in keys:
        keys.append(unknown)
        del mapping[key]
    return mapping


def escaped_keys(mapping, keys):
    notify(keys)
    for key in keys:
        del mapping[key]
    return mapping


def alias_escape(mapping, other):
    notify(other)
    return mapping


def alias_root(**kwargs):
    return alias_escape(kwargs, kwargs)


def unclear(mapping, flag):
    if flag:
        mapping.clear()
    return mapping


def recursive(mapping):
    return recursive(mapping)


def bad_tuple(mapping, flag):
    if flag:
        return mapping, 0
    return 0, mapping


def unknown_input(mapping):
    return normalize((), mapping)


def finite_root(value):
    result = normalize((), {'allowed': value})
    return fixed(**result)


def clear_after(**kwargs):
    result = normalize((), kwargs)
    result.clear()
    return fixed(**result)


def clear_before(**kwargs):
    kwargs.clear()
    return fixed(**normalize((), kwargs))


def copy_before(**kwargs):
    copy = dict(kwargs)
    copy.clear()
    return fixed(**normalize((), kwargs))


def filter_root(**kwargs):
    filter_keys(kwargs, ['before', 'out'])
    return fixed(**kwargs)


def unknown_keys(keys, **kwargs):
    filter_keys(kwargs, keys)
    return fixed(**kwargs)


def unsafe_root(**kwargs):
    return changed(kwargs)


def escaped_global(**kwargs):
    global SAVED
    SAVED = kwargs
    return normalize((), kwargs)


def captured_alias(**kwargs):
    callback = lambda: kwargs.clear()
    return apply_callback(kwargs, callback)


def apply_callback(mapping, callback):
    callback()
    return mapping


def self_reference(**kwargs):
    kwargs['self'] = kwargs
    return hidden_alias(kwargs)


def hidden_alias(mapping):
    alias = mapping.get('self')
    alias.clear()
    return mapping


def branch_keys(flag, **kwargs):
    if flag:
        keys = ['p']
    else:
        keys = ['w']
    filter_keys(kwargs, keys)
    return fixed(**kwargs)


def modified_keys(**kwargs):
    keys = ['p']
    notify(keys)
    filter_keys(kwargs, keys)
    return fixed(**kwargs)
