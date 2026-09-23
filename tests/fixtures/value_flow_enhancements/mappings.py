def validate_take(args, kwargs):
    return kwargs


def mapping_operations(flag, other, replacement, **kwargs):
    epsilon = kwargs.pop("epsilon")
    observed = "gather_statistics" in kwargs
    if flag:
        del kwargs["gather_statistics"]
    kwargs.update(other)
    merged = {**kwargs, "min_delta": epsilon}
    return validate_take((), kwargs), merged, observed, replacement
