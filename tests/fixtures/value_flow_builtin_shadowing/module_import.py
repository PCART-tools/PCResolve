if flag:
    from replacements import mapping as dict, sequence as list, sequence as tuple


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
