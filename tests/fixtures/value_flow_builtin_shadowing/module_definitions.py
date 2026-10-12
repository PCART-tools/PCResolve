if flag:
    def dict(value):
        return {'value': 0}

    def list(value):
        return ()

    class tuple:
        pass


def mapping_call(**kwargs):
    return dict(kwargs)


def list_call(*args):
    return list(args)


def tuple_call(*args):
    return tuple(args)
