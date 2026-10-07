def fixed(allowed=0):
    return allowed


def accepts(**kwargs):
    return kwargs


def invoke(metric, mapping):
    return metric(**mapping)


def relay(callback, mapping):
    alias = callback
    return invoke(alias, mapping)


def replace(metric, mapping):
    metric = accepts
    return metric(**mapping)


def conditional(metric, mapping, flag):
    if flag:
        metric = accepts
    return metric(**mapping)


def overwrite(metric, mapping):
    metric.__code__ = unknown_code
    return metric(**mapping)
