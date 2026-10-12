if flag:
    from replacements import *


def mapping_call(**kwargs):
    return dict(kwargs)


def list_call(*args):
    return list(args)


def tuple_call(*args):
    return tuple(args)
