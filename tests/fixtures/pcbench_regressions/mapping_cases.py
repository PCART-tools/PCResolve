# Reduced from Keras 2.1.6, Dask 2022.4.2, and pandas 2.0.0.
def validate_take(args, kwargs):
    return kwargs


def keras_reduce_lr(**kwargs):
    if "epsilon" in kwargs:
        min_delta = kwargs.pop("epsilon")
    else:
        min_delta = 0
    return min_delta


def dask_gather(flag, **kwargs):
    if flag and "gather_statistics" in kwargs:
        kwargs.pop("gather_statistics")
    return kwargs


def pandas_series_take(**kwargs):
    validate_take((), kwargs)
