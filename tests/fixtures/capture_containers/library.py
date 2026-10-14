def fixed(value=None):
    return value


def fixed_args(value=None):
    return value


def helper(mapping):
    return fixed(**mapping)


def direct(**kwargs):
    def inner():
        return fixed(**kwargs)
    return inner()


def alias(**kwargs):
    options = kwargs
    def inner():
        return fixed(**options)
    return inner()


def positional(*args):
    def inner():
        return fixed_args(*args)
    return inner()


def copied(**kwargs):
    def inner():
        return fixed(**kwargs.copy())
    return inner()


def pop(**kwargs):
    def inner():
        kwargs.pop('out', None)
        return fixed(**kwargs)
    return inner()


def through_helper(**kwargs):
    def inner():
        return helper(kwargs)
    return inner()


def nested(**kwargs):
    def inner():
        def deepest():
            return fixed(**kwargs)
        return deepest()
    return inner()


def rebound_open(**kwargs):
    options = {}
    def inner():
        return fixed(**options)
    options = kwargs
    return inner()


def rebound_finite(**kwargs):
    def inner():
        return fixed(**kwargs)
    kwargs = {'value': 0}
    return inner()


def cleared_before(**kwargs):
    def inner():
        return fixed(**kwargs)
    kwargs.clear()
    return inner()


def cleared_inside(**kwargs):
    def inner():
        kwargs.clear()
        return fixed(**kwargs)
    return inner()


def nonlocal_finite(**kwargs):
    def inner():
        nonlocal kwargs
        kwargs = {'value': 0}
        return fixed(**kwargs)
    return inner()


def shadowed(**kwargs):
    def inner(kwargs):
        return fixed(**kwargs)
    return inner({'value': 0})


def unknown_effect(**kwargs):
    def inner():
        opaque(kwargs)
        return fixed(**kwargs)
    return inner()


def unknown_before(**kwargs):
    def inner():
        return fixed(**kwargs)
    opaque(kwargs)
    return inner()


def returned(**kwargs):
    def inner():
        return fixed(**kwargs)
    return inner


def unused(**kwargs):
    def inner():
        return fixed(**kwargs)
    return 0


def impossible(**kwargs):
    def inner():
        if False:
            return fixed(**kwargs)
    return inner()


def two_calls(**kwargs):
    def inner():
        return fixed(**kwargs)
    inner()
    kwargs.clear()
    return inner()


def unrelated_capture(config, **kwargs):
    def inner():
        return config
    return inner()


def identity_return(**kwargs):
    def inner():
        return kwargs
    return fixed(**inner())


def multiple(*args, **kwargs):
    def inner():
        fixed_args(*args)
        return fixed(**kwargs)
    return inner()


def argument_clear(**kwargs):
    def inner(unused):
        return fixed(**kwargs)
    return inner(kwargs.clear())


def generator(**kwargs):
    def inner():
        yield fixed(**kwargs)
    return inner()


def asynchronous(**kwargs):
    async def inner():
        return fixed(**kwargs)
    return inner()


def middle_shadow(**kwargs):
    def inner(kwargs):
        def deepest():
            return fixed(**kwargs)
        return deepest()
    return inner({'value': 0})


def sibling_clear(**kwargs):
    def clear():
        nonlocal kwargs
        kwargs = {'value': 0}
    def inner():
        return fixed(**kwargs)
    clear()
    return inner()


def shared_alias_clear(**kwargs):
    options = kwargs
    def inner():
        options.clear()
        return fixed(**kwargs)
    return inner()


def separate_copy_clear(**kwargs):
    options = kwargs.copy()
    def inner():
        options.clear()
        return fixed(**kwargs)
    return inner()
