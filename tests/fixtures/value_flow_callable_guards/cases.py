from helpers import imported_fixed
import helpers


def fixed(allowed=None):
    return allowed


def accepts(**kwargs):
    return kwargs


def positive(metric, **kwargs):
    if metric is fixed:
        return metric(**kwargs)


def reversed_guard(metric, **kwargs):
    if fixed is metric:
        return metric(**kwargs)


def negative_else(metric, **kwargs):
    if metric is not fixed:
        return None
    else:
        return metric(**kwargs)


def negative_early_return(metric, **kwargs):
    if metric is not fixed:
        return None
    return metric(**kwargs)


def negated_guard(metric, **kwargs):
    if not (metric is not fixed):
        return metric(**kwargs)


def conjunction(metric, enabled, **kwargs):
    if metric is fixed and enabled:
        return metric(**kwargs)


def short_circuit(metric, **kwargs):
    return metric is fixed and metric(**kwargs)


def short_circuit_or(metric, **kwargs):
    return metric is not fixed or metric(**kwargs)


def conditional_expression(metric, **kwargs):
    return metric(**kwargs) if metric is fixed else None


def conditional_negative(metric, **kwargs):
    return None if metric is not fixed else metric(**kwargs)


def imported_guard(metric, **kwargs):
    if metric is imported_fixed:
        return metric(**kwargs)


def module_guard(metric, **kwargs):
    if metric is helpers.imported_fixed:
        return metric(**kwargs)


def alias_after_guard(metric, **kwargs):
    if metric is fixed:
        chosen = metric
        return chosen(**kwargs)


def equality(metric, **kwargs):
    if metric == fixed:
        return metric(**kwargs)


def unequal_branch(metric, **kwargs):
    if metric is not fixed:
        return metric(**kwargs)


def false_branch(metric, **kwargs):
    if metric is fixed:
        return None
    else:
        return metric(**kwargs)


def unguarded_after_join(metric, **kwargs):
    if metric is fixed:
        pass
    return metric(**kwargs)


def rebound(metric, **kwargs):
    if metric is fixed:
        metric = accepts
        return metric(**kwargs)


def shadowed_target(metric, fixed, **kwargs):
    if metric is fixed:
        return metric(**kwargs)


def shadowed_module(metric, helpers, **kwargs):
    if metric is helpers.imported_fixed:
        return metric(**kwargs)


def local_target_rebound(metric, **kwargs):
    fixed = accepts
    if metric is fixed:
        return metric(**kwargs)


def escaped(metric, **kwargs):
    if metric is fixed:
        opaque(metric)
        return metric(**kwargs)


def modified(metric, **kwargs):
    if metric is fixed:
        metric.__code__ = opaque_code
        return metric(**kwargs)


def chained(metric, other, **kwargs):
    if metric is fixed is other:
        return metric(**kwargs)


def callable_only(metric, **kwargs):
    if callable(metric):
        return metric(**kwargs)


def finite(metric, **kwargs):
    if metric is fixed:
        return metric(**{'allowed': kwargs.get('allowed')})


def cleared(metric, **kwargs):
    if metric is fixed:
        kwargs.clear()
        return metric(**kwargs)


def contradictory(metric, **kwargs):
    if metric is fixed:
        if metric is accepts:
            return metric(**kwargs)


def known_other(**kwargs):
    return positive(accepts, **kwargs)


def known_same(**kwargs):
    return positive(fixed, **kwargs)


def contexts(other, **kwargs):
    positive(accepts, **kwargs)
    positive(fixed, **kwargs)
    return positive(other, **kwargs)


def decorate(function):
    return accepts


@decorate
def decorated(allowed=None):
    return allowed


def decorated_guard(metric, **kwargs):
    if metric is decorated:
        return metric(**kwargs)


def known_string(**kwargs):
    return positive('fixed', **kwargs)


def finite_alternatives(enabled, **kwargs):
    metric = fixed if enabled else accepts
    if metric is not fixed:
        return metric(**kwargs)


def contradictory_alternatives(enabled, **kwargs):
    metric = fixed if enabled else accepts
    if metric is fixed:
        if metric is accepts:
            return metric(**kwargs)


def rebound_in_condition(metric, **kwargs):
    if metric is fixed and (metric := accepts):
        return metric(**kwargs)


def unknown_expansion(metric, values, **kwargs):
    return positive(*values, **kwargs)


def invalid_duplicate(**kwargs):
    return positive(accepts, metric=fixed, **kwargs)
