## @package exports.leaf
#  Distinct definitions used to test reexport resolution.


def together(expr, *args, **kwargs):
    return expr, args, kwargs


def other(expr, *args, **kwargs):
    return kwargs
