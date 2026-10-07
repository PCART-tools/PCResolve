from scipy.spatial.distance import euclidean, _args_to_kwargs_xdist, _filter_deprecated_kwargs


def invoke(metric, mapping):
    return metric(**mapping)


def sink(**kwargs):
    return kwargs


def callback_control(**kwargs):
    return invoke(euclidean, kwargs)


def early_control(**kwargs):
    mapping = _args_to_kwargs_xdist((), kwargs, euclidean, 'cdist')
    mapping.pop('out', None)
    return sink(**mapping)


def deletion_control(**kwargs):
    _filter_deprecated_kwargs(kwargs, ('out', 'p'))
    return sink(**kwargs)
