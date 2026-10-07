from helpers import fixed, accepts, invoke, relay, replace, conditional, overwrite
import helpers as api


def root(**kwargs):
    return invoke(fixed, kwargs)


def aliased(**kwargs):
    callback = fixed
    return relay(callback, kwargs)


def contexts(**kwargs):
    return invoke(fixed, kwargs), invoke(accepts, kwargs)


def mixed(callback, **kwargs):
    return invoke(fixed, kwargs), invoke(callback, kwargs)


def rebound(**kwargs):
    return replace(fixed, kwargs)


def branch(flag, **kwargs):
    return conditional(fixed, kwargs, flag)


def modified(**kwargs):
    return overwrite(fixed, kwargs)


def unknown(callback, **kwargs):
    return invoke(callback, kwargs)


def named(**kwargs):
    return invoke('fixed', kwargs)


TARGETS = {'fixed': fixed, 'accepts': accepts}


def literal_dispatch(**kwargs):
    return TARGETS['fixed'](**kwargs)


def variable_dispatch(key, **kwargs):
    return TARGETS[key](**kwargs)


def local_dispatch(**kwargs):
    table = {'fixed': fixed}
    return table['fixed'](**kwargs)


DIRTY = {'fixed': fixed}
DIRTY['fixed'] = unknown_factory()


def dirty_dispatch(**kwargs):
    return DIRTY['fixed'](**kwargs)


ESCAPED = {'fixed': fixed}


def escape_table():
    unknown_effect(ESCAPED)


def escaped_dispatch(**kwargs):
    return ESCAPED['fixed'](**kwargs)


INCOMPLETE = {'fixed': fixed, 'other': unknown_factory()}


def incomplete_dispatch(key, **kwargs):
    return INCOMPLETE[key](**kwargs)


def escaped_local(**kwargs):
    table = {'fixed': fixed}
    unknown_effect(table)
    return table['fixed'](**kwargs)


def callback_escape(**kwargs):
    callback = fixed
    unknown_effect(callback)
    return invoke(callback, kwargs)


def module_alias(**kwargs):
    return invoke(api.fixed, kwargs)


def mixed_actual(callback, flag, **kwargs):
    metric = fixed
    if flag:
        metric = callback
    return invoke(metric, kwargs)


def modified_table_value(**kwargs):
    table = {'fixed': fixed}
    table['fixed'].__code__ = unknown_code
    return table['fixed'](**kwargs)


def removed_callback(callback, flag, mapping):
    if flag:
        del callback
    return callback(**mapping)


def removed_root(flag, **kwargs):
    return removed_callback(fixed, flag, kwargs)


def relay_contexts(**kwargs):
    return relay(fixed, kwargs), relay(accepts, kwargs)


def module_table_shadow(**kwargs):
    fixed = accepts
    return TARGETS['fixed'](**kwargs)
