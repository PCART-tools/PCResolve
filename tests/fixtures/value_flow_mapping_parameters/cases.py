## @package value_flow_mapping_parameters.cases


def remove_out(mapping):
    mapping.pop('out', None)


def delete_out(mapping):
    del mapping['out']


def alias_remove(mapping):
    alias = mapping
    alias.pop('out', None)


def alias_delete(mapping):
    alias = mapping
    del alias['out']


def clean(mapping):
    mapping.pop('out', None)
    return mapping


def clean_alias(mapping):
    alias = mapping
    alias.pop('out', None)
    return alias


def clean_delete(mapping):
    del mapping['out']
    return mapping


def required_pop(mapping):
    mapping.pop('out')


def popped(mapping):
    return mapping.pop('out', None)


def fixed(w=None):
    return w


def sink(**mapping):
    return mapping


def identity(mapping):
    return mapping


def root_inplace(**kwargs):
    remove_out(kwargs)
    return fixed(**kwargs)


def root_return(**kwargs):
    forwarded = clean(kwargs)
    return fixed(**forwarded)


def root_delete(**kwargs):
    delete_out(kwargs)
    return sink(**kwargs)


def root_alias(**kwargs):
    alias_remove(kwargs)
    return sink(**kwargs)


def root_alias_delete(**kwargs):
    alias_delete(kwargs)
    return sink(**kwargs)


def root_return_alias(**kwargs):
    forwarded = clean_alias(kwargs)
    forwarded.pop('other', None)
    original = {**kwargs}
    return original, forwarded


def root_return_delete(**kwargs):
    forwarded = clean_delete(kwargs)
    return kwargs, forwarded


def root_clear(**kwargs):
    forwarded = clean(kwargs)
    forwarded.clear()
    return kwargs, forwarded


def two_inputs(x, y):
    first = {'out': x, 'keep': y}
    second = {'out': y}
    clean(first)
    return first, second


def repeated_calls(x, y):
    first = {'out': x, 'keep': y}
    second = {'out': y, 'other': x}
    a = clean(first)
    b = clean(second)
    return a, b


def finite(x, y):
    original = {'out': x, 'keep': y}
    forwarded = clean(original)
    return sink(**forwarded)


def keyword_binding(**kwargs):
    remove_out(mapping=kwargs)
    return sink(**kwargs)


def expanded_binding(**kwargs):
    remove_out(*(kwargs,))
    return sink(**kwargs)


def returned_input(**kwargs):
    mapping = identity(kwargs)
    remove_out(mapping)
    return kwargs, mapping


def root_required(**kwargs):
    required_pop(kwargs)
    return sink(**kwargs)


def catch_required(**kwargs):
    try:
        required_pop(kwargs)
    except KeyError:
        pass
    return sink(**kwargs)


def catch_delete(**kwargs):
    try:
        delete_out(kwargs)
    except KeyError:
        pass
    return sink(**kwargs)


def root_popped(**kwargs):
    value = popped(kwargs)
    value.clear()
    return kwargs, value


def recapture(**mapping):
    mapping.pop('out', None)
    return mapping


def root_recapture(**kwargs):
    forwarded = recapture(**kwargs)
    forwarded.clear()
    return sink(**kwargs)


def copied(mapping):
    copy = mapping.copy()
    copy.pop('out', None)
    return copy


def root_copy(**kwargs):
    forwarded = copied(kwargs)
    forwarded.clear()
    return sink(**kwargs)


def dynamic_key(mapping, key):
    mapping.pop(key, None)
    return mapping


def conditional(mapping, flag):
    if flag:
        mapping.pop('out', None)
    return mapping


def unknown_write(mapping):
    mapping.pop('out', None)
    mapping['out'] = None
    return mapping


def escaping(mapping):
    mapping.pop('out', None)
    external(mapping)
    return mapping


def recursive(mapping):
    mapping.pop('out', None)
    return recursive(mapping)


def caught(mapping):
    try:
        del mapping['out']
    except KeyError:
        mapping['out'] = None
    return mapping


def limited(mapping):
    alias = mapping
    alias.pop('out', None)
    alias.pop('other', None)
    return alias


def unknown_receiver(mapping):
    remove_out(mapping)
    return mapping


def annotated_receiver(mapping: dict):
    remove_out(mapping)
    return mapping


def negative_key(key, **kwargs):
    dynamic_key(kwargs, key)
    return sink(**kwargs)


def negative_conditional(flag, **kwargs):
    conditional(kwargs, flag)
    return sink(**kwargs)


def negative_write(**kwargs):
    unknown_write(kwargs)
    return sink(**kwargs)


def negative_escape(**kwargs):
    escaping(kwargs)
    return sink(**kwargs)


def negative_recursive(**kwargs):
    recursive(kwargs)
    return sink(**kwargs)


def negative_caught(**kwargs):
    caught(kwargs)
    return sink(**kwargs)


def negative_budget(**kwargs):
    limited(kwargs)
    return kwargs


def mixed_binding(flag, unknown, **kwargs):
    mapping = kwargs if flag else unknown
    remove_out(mapping)
    return sink(**kwargs)


def two_known(flag, x, y):
    first = {'out': x}
    second = {'out': y}
    mapping = first if flag else second
    remove_out(mapping)
    return first, second


def uncertain_binding(args, **kwargs):
    remove_out(*args, **kwargs)
    return sink(**kwargs)


def in_caller_branch(flag, **kwargs):
    if flag:
        remove_out(kwargs)
    return sink(**kwargs)


def replacement(mapping):
    return {}


def modified_callable(**kwargs):
    clean.__code__ = replacement.__code__
    forwarded = clean(kwargs)
    forwarded.clear()
    return sink(**kwargs)


def decorator(fn):
    return fn


@decorator
def decorated(mapping):
    mapping.pop('out', None)
    return mapping


def negative_decorator(**kwargs):
    forwarded = decorated(kwargs)
    forwarded.clear()
    return sink(**kwargs)


def repeated_pop(mapping):
    mapping.pop('out', None)
    return mapping.pop('out', None)


def root_popped_finite(value):
    mapping = {'out': value}
    return popped(mapping)


def root_repeated_pop(**kwargs):
    return repeated_pop(kwargs)


def unknown_after_removal(**kwargs):
    remove_out(kwargs)
    escaping(kwargs)
    return sink(**kwargs)


def mismatched_shape(value):
    mapping = [value]
    remove_out(mapping)
    return mapping


def generator(mapping):
    mapping.pop('out', None)
    return mapping
    yield None


def negative_generator(**kwargs):
    generator(kwargs)
    return sink(**kwargs)


def loop_keys(mapping):
    for key in ('out', 'other'):
        mapping.pop(key, None)
    return mapping


def negative_loop(**kwargs):
    loop_keys(kwargs)
    return sink(**kwargs)


from helpers import clean as imported_clean


def cross_module(**kwargs):
    forwarded = imported_clean(kwargs)
    return kwargs, forwarded


def loop_unknown(unknown, **kwargs):
    mapping = kwargs
    for marker in (0, 1):
        clean(mapping)
        mapping = unknown
    return sink(**kwargs)


def clear_return(mapping):
    mapping.clear()
    return mapping


def modified_clear_return(**kwargs):
    clear_return.__code__ = replacement.__code__
    forwarded = clear_return(kwargs)
    return sink(**kwargs)


def capture_clear(**mapping):
    mapping.clear()


def root_capture_clear(**kwargs):
    capture_clear(**kwargs)
    return sink(**kwargs)


def empty_mapping_root(**kwargs):
    kwargs.clear()
    remove_out(kwargs)
    return kwargs


def unknown_empty_mapping_root(**kwargs):
    kwargs.clear()
    escaping(kwargs)
    return kwargs
