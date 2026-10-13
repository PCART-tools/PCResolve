def change(flag):
    global dict, list, tuple
    if flag:
        dict = replacement
        list = replacement
        tuple = replacement


def mapping_call(**kwargs):
    global dict
    return dict(kwargs)


def list_call(*args):
    return list(args)


def tuple_call(*args):
    global tuple
    return tuple(args)
