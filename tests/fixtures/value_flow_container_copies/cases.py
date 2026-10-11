def sink(*args, **kwargs):
    return args, kwargs


def copy_open(**kwargs):
    copied = kwargs.copy()
    copied.pop('out', None)
    return sink(**copied)


def dict_open(**kwargs):
    copied = dict(kwargs)
    copied.pop('out', None)
    return sink(**copied)


def clear_copy(**kwargs):
    copied = kwargs.copy()
    copied.clear()
    sink(**copied)
    return sink(**kwargs)


def clear_original(**kwargs):
    copied = dict(kwargs)
    kwargs.clear()
    sink(**kwargs)
    return sink(**copied)


def copy_cleared(**kwargs):
    kwargs.clear()
    copied = kwargs.copy()
    return sink(**copied)


def dict_cleared(**kwargs):
    kwargs.clear()
    copied = dict(kwargs)
    return sink(**copied)


def finite_copy(value):
    original = {'allowed': value}
    copied = original.copy()
    original.clear()
    return sink(**copied)


def excluded_copy(**kwargs):
    kwargs.pop('out', None)
    copied = dict(kwargs)
    return sink(**copied)


def shallow_copy(value):
    payload = [value]
    original = {'payload': payload}
    copied = original.copy()
    copied['payload'].clear()
    return sink(original)


def repeated_copies(x, y):
    first = {'allowed': x}.copy()
    second = dict({'allowed': y})
    first.clear()
    return sink(**second)


def list_args(*args):
    copied = list(args)
    copied.clear()
    sink(*copied)
    return sink(*args)


def tuple_list(value):
    original = [value]
    copied = tuple(original)
    original.clear()
    return sink(*copied)


def list_finite(x, y):
    copied = list((x, y))
    copied.pop(0)
    return copied[0]


def tuple_args(*args):
    copied = tuple(args)
    return sink(*copied)


def list_cleared(value):
    original = [value]
    original.clear()
    copied = list(original)
    return sink(*copied)


def setdefault_present(existing, default):
    mapping = {'out': existing}
    value = mapping.setdefault('out', default)
    sink(**mapping)
    return value


def setdefault_missing(other, default):
    mapping = {'allowed': other}
    value = mapping.setdefault('out', default)
    sink(**mapping)
    return value


def setdefault_unknown(default, **kwargs):
    value = kwargs.setdefault('out', default)
    sink(**kwargs)
    return value


def setdefault_excluded(default, **kwargs):
    kwargs.pop('out', None)
    value = kwargs.setdefault('out', default)
    sink(**kwargs)
    return value


def setdefault_after_clear(default, **kwargs):
    kwargs.clear()
    value = kwargs.setdefault('out', default)
    sink(**kwargs)
    return value


def setdefault_none(value):
    mapping = {'allowed': value}
    mapping.setdefault('out')
    return sink(**mapping)


def setdefault_existing_none(default):
    mapping = {'out': None}
    return mapping.setdefault('out', default)


def setdefault_alias(default, **kwargs):
    alias = kwargs
    alias.setdefault('out', default)
    return sink(**kwargs)


def setdefault_nested(value):
    mapping = {}
    payload = mapping.setdefault('payload', [value])
    payload.clear()
    return sink(mapping)


def setdefault_twice(first, second, **kwargs):
    kwargs.setdefault('out', first)
    return kwargs.setdefault('out', second)


def default_eager(value):
    mapping = {'out': value}
    mapping.setdefault('out', mapping.clear())
    return sink(**mapping)


def setdefault_dynamic(key, default, **kwargs):
    kwargs.setdefault(key, default)
    return sink(**kwargs)


def mixed_copy(flag, value, unknown):
    if flag:
        mapping = {'allowed': value}
    else:
        mapping = unknown
    copied = mapping.copy()
    return copied.clear()


def unknown_copy(mapping):
    copied = mapping.copy()
    return copied.clear()


def unknown_dict(mapping):
    copied = dict(mapping)
    return copied.clear()


def projected_copy(**kwargs):
    copied = kwargs['payload'].copy()
    return copied.clear()


def shadowed_dict(dict, **kwargs):
    copied = dict(kwargs)
    return copied.clear()


def shadowed_list(list, *args):
    copied = list(args)
    return copied.clear()


def local_shadow(**kwargs):
    dict = unknown_factory
    copied = dict(kwargs)
    return copied.clear()


class Custom:
    def copy(self):
        return self

    def setdefault(self, key, default):
        return default


def custom_copy(**kwargs):
    original = Custom()
    copied = original.copy()
    return copied.clear()


def custom_default(value):
    original = Custom()
    return original.setdefault('out', value)


def invalid_copy(**kwargs):
    return kwargs.copy(1)


def invalid_default(value, **kwargs):
    return kwargs.setdefault(key='out', default=value)


def conditional_copy(flag, **kwargs):
    if flag:
        kwargs.clear()
    copied = kwargs.copy()
    return sink(**copied)


def copy_escape(**kwargs):
    kwargs.pop('out', None)
    external(kwargs)
    copied = kwargs.copy()
    return sink(**copied)


def tuple_identity(*args):
    copied = tuple(args)
    return copied


def conditional_key(flag, existing, default):
    mapping = {}
    if flag:
        mapping['out'] = existing
    return mapping.setdefault('out', default)


def unknown_default_container(value, **kwargs):
    payload = kwargs.setdefault('payload', [value])
    return payload.clear()


def escaped_finite(value, default):
    mapping = {'out': value}
    external(mapping)
    return mapping.setdefault('out', default)


def returned_alias_copy(**kwargs):
    original = identity(kwargs)
    copied = original.copy()
    kwargs.clear()
    return sink(**copied)


def identity(mapping):
    return mapping


def copied_sequence_nested(value):
    payload = [value]
    original = [payload]
    copied = list(original)
    copied[0].clear()
    return sink(original)


def default_existing_container(value, default):
    mapping = {'payload': [value]}
    payload = mapping.setdefault('payload', default)
    payload.clear()
    return sink(mapping)


def copied_get_default(flag, existing, default):
    mapping = {}
    if flag:
        mapping['out'] = existing
    copied = mapping.copy()
    return copied.get('out', default)
