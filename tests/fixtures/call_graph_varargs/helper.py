def apply_reshape(value):
    return value.reshape(1, -1)


def forward_varargs(*args):
    return apply_reshape(*args)


def forward_kwargs(**kwargs):
    return apply_reshape(**kwargs)
