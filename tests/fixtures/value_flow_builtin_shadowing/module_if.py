from replacements import mapping, sequence


if flag:
    dict = mapping
    list = sequence
    tuple = sequence


def mapping_call(**kwargs):
    return dict(kwargs)


def list_call(*args):
    return list(args)


def tuple_call(*args):
    return tuple(args)


def ordinary_list(value):
    return list(value)


def ordinary_tuple(value):
    return tuple(value)
