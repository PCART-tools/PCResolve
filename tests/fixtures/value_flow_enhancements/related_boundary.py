import broken


def entry(value):
    return broken.unavailable(value)


def unused(value, **kwargs):
    return broken.unavailable(value)


def reflected(value, **kwargs):
    return eval('kwargs')
