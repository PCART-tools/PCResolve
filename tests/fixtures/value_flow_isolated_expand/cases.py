def fixed(allowed=0):
    return allowed


def accepts(**kwargs):
    return kwargs


TARGETS = {'fixed': fixed, 'accepts': accepts}


def recursive(metric, **kwargs):
    if isinstance(metric, str):
        return recursive(TARGETS[metric], **kwargs)
    return metric(**kwargs)


def rebound(metric, **kwargs):
    metric = accepts
    return metric(**kwargs)


def invoke(metric, **kwargs):
    return metric(**kwargs)


def mixed(**kwargs):
    invoke(accepts, **kwargs)
    return invoke(fixed, **kwargs)


def loop(metric, **kwargs):
    return loop(metric, **kwargs)
