## @package value_flow_return_objects.cases


def identity(mapping):
    return mapping


def alias_identity(mapping):
    alias = mapping
    return alias


def fixed(w=None):
    return w


def sink(**mapping):
    return mapping


def root(**kwargs):
    mapping = identity(kwargs)
    mapping.pop('out', None)
    return fixed(**mapping)


def alias_clear(**kwargs):
    mapping = alias_identity(kwargs)
    mapping.clear()
    return sink(**kwargs)


def two_inputs(x, y):
    left = {'left': x}
    right = {'right': y}
    a = identity(left)
    b = identity(right)
    a.clear()
    return sink(**right)


def update_alias(value, **kwargs):
    mapping = identity(kwargs)
    mapping.update(added=value)
    return sink(**kwargs)


def list_alias(x, y):
    original = [x, y]
    returned = identity(original)
    returned.pop(0)
    return original


def tuple_alias(x):
    original = (x,)
    returned = identity(original)
    return returned[0]


def repeat_identity(**kwargs):
    first = identity(kwargs)
    second = alias_identity(first)
    second.pop('out', None)
    return sink(**kwargs)


def finite_input(value):
    original = {'allowed': value}
    returned = identity(original)
    returned.pop('out', None)
    return sink(**returned)


def recapture(**mapping):
    return mapping


def copy_mapping(mapping):
    return mapping.copy()


def rebuild(mapping):
    return {'allowed': mapping['allowed']}


def payload(mapping):
    return mapping['payload']


def arithmetic(mapping):
    return mapping + 1


def boolean(mapping):
    return bool(mapping)


def mixed(mapping, unknown, flag):
    if flag:
        return mapping
    return unknown


def implicit(mapping, flag):
    if flag:
        return mapping


def mutate(mapping):
    mapping['changed'] = None
    return mapping


def escape(mapping):
    external(mapping)
    return mapping


def finalized(mapping):
    try:
        return mapping
    finally:
        mapping.clear()


def recursive(mapping):
    return recursive(mapping)


def long_alias(mapping):
    one = mapping
    two = one
    three = two
    return three


def negative_recapture(**kwargs):
    returned = recapture(**kwargs)
    returned.clear()
    return sink(**kwargs)


def negative_copy(**kwargs):
    returned = copy_mapping(kwargs)
    returned.clear()
    return sink(**kwargs)


def negative_rebuild(**kwargs):
    returned = rebuild(kwargs)
    returned.pop('out', None)
    return sink(**kwargs)


def negative_payload(**kwargs):
    returned = payload(kwargs)
    returned.clear()
    return sink(**kwargs)


def negative_arithmetic(**kwargs):
    returned = arithmetic(kwargs)
    returned.clear()
    return sink(**kwargs)


def negative_boolean(**kwargs):
    returned = boolean(kwargs)
    returned.clear()
    return sink(**kwargs)


def negative_mixed(unknown, flag, **kwargs):
    returned = mixed(kwargs, unknown, flag)
    returned.clear()
    return sink(**kwargs)


def negative_implicit(flag, **kwargs):
    returned = implicit(kwargs, flag)
    returned.clear()
    return sink(**kwargs)


def negative_mutate(**kwargs):
    returned = mutate(kwargs)
    returned.pop('out', None)
    return sink(**kwargs)


def negative_escape(**kwargs):
    returned = escape(kwargs)
    returned.clear()
    return sink(**kwargs)


def negative_finalized(**kwargs):
    returned = finalized(kwargs)
    returned.clear()
    return sink(**kwargs)


def negative_recursive(**kwargs):
    returned = recursive(kwargs)
    returned.clear()
    return sink(**kwargs)


def unknown_input(mapping):
    returned = identity(mapping)
    return returned.pop('out', None)


def uncertain_binding(args, **kwargs):
    returned = identity(*args, **kwargs)
    return returned.pop('out', None)


def transformed_alias(flag, **kwargs):
    returned = identity(kwargs)
    selected = returned['payload']
    selected.clear()
    compared = returned == None
    compared.clear()
    if flag:
        partial = returned
    partial.clear()
    return sink(**kwargs)


def direct_clear(**kwargs):
    kwargs.clear()
    return sink(**kwargs)


def direct_pop(**kwargs):
    kwargs.pop('out', None)
    return fixed(**kwargs)


def return_cleared(**kwargs):
    returned = identity(kwargs)
    returned.clear()
    return returned


def return_popped(**kwargs):
    returned = identity(kwargs)
    returned.pop('out', None)
    return returned


def returned_membership(**kwargs):
    returned = identity(kwargs)
    return 'out' in returned


def returned_delete(**kwargs):
    returned = identity(kwargs)
    del returned['out']
    return sink(**kwargs)


def merge_returned(value):
    original = {'allowed': value}
    returned = identity(original)
    copy = {**returned}
    copy.clear()
    return sink(**original)


def clear_only(mapping):
    mapping.clear()


def existing_clear_effect(**kwargs):
    returned = identity(kwargs)
    clear_only(returned)
    return sink(**kwargs)


def budget_alias(**kwargs):
    returned = long_alias(kwargs)
    return returned.pop('out', None)


def keyword_alias(**kwargs):
    returned = identity(mapping=kwargs)
    returned.clear()
    return sink(**kwargs)


def expanded_alias(**kwargs):
    returned = identity(*(kwargs,))
    returned.pop('out', None)
    return sink(**kwargs)


def derived_before_clear(**kwargs):
    returned = identity(kwargs)
    comparison = returned == None
    returned.clear()
    return comparison


def derived_after_clear(**kwargs):
    returned = identity(kwargs)
    returned.clear()
    return returned == None


def packed(**kwargs):
    return [identity(kwargs)]


def packed_mapping(**kwargs):
    returned = identity(kwargs)
    return {'payload': returned}


def packed_cleared(**kwargs):
    returned = identity(kwargs)
    returned.clear()
    return [returned]


def unreachable_generator(mapping):
    return mapping
    yield None


def unreachable_generator_from(mapping):
    return mapping
    yield from ()


def negative_generator(**kwargs):
    returned = unreachable_generator(kwargs)
    returned.clear()
    return sink(**kwargs)


def negative_generator_from(**kwargs):
    returned = unreachable_generator_from(kwargs)
    returned.clear()
    return sink(**kwargs)


def mixed_effects(mapping, local):
    external(mapping)
    return mapping


def chained_unproven(**kwargs):
    current = escape(kwargs)
    return mixed_effects(current, {})


def loop_unknown(unknown, **kwargs):
    current = kwargs
    for marker in (0, 1):
        returned = identity(current)
        returned.pop('out', None)
        current = unknown
    return kwargs


def replacement(mapping):
    return {}


def modified_callable(**kwargs):
    identity.__code__ = replacement.__code__
    returned = identity(kwargs)
    returned.clear()
    return sink(**kwargs)


def modified_callable_alias(**kwargs):
    alias = identity
    alias.__code__ = replacement.__code__
    returned = identity(kwargs)
    returned.clear()
    return sink(**kwargs)


def modified_nested_callable(**kwargs):
    def local(mapping):
        return mapping
    local.__code__ = replacement.__code__
    returned = local(kwargs)
    returned.clear()
    return sink(**kwargs)
