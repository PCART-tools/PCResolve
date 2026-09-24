import provider as nv
from provider import validator as aliased_validator


def accepted(**kwargs):
    return nv.validator((), kwargs)


def accepted_import_alias(**kwargs):
    return aliased_validator((), kwargs)


def reassigned(**kwargs):
    return nv.reassigned((), kwargs)


def unknown_factory(**kwargs):
    return nv.unknown((), kwargs)


def dynamically_modified(**kwargs):
    return nv.modified((), kwargs)


def conditionally_bound(**kwargs):
    return nv.conditional((), kwargs)


def class_name_rebound(**kwargs):
    return nv.class_rebound((), kwargs)


def unknown_parameter(receiver, **kwargs):
    return receiver((), kwargs)


def shadowed_alias(nv, **kwargs):
    return nv.validator((), kwargs)
