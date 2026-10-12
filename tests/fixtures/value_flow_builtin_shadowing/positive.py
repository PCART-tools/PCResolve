def mapping_call(**kwargs):
    return dict(kwargs)


def list_call(*args):
    return list(args)


def tuple_call(*args):
    return tuple(args)


def ordinary_sequence(value):
    return tuple(value)


def global_read(**kwargs):
    global dict
    return dict(kwargs)


def outer():
    global list

    def inner(*args):
        return list(args)
    return inner


class Owner:
    dict = unknown

    def method(self, **kwargs):
        return dict(kwargs)


def local_copy(**kwargs):
    copied = dict(kwargs)
    copied.clear()
    return kwargs


def cleared_copy(**kwargs):
    kwargs.clear()
    return dict(kwargs)
