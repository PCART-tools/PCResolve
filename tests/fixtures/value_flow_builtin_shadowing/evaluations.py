def replacement(value):
    return ()


def ignored(value=(dict := replacement)):
    pass


ignored_lambda = lambda value=(tuple := replacement): None


def mapping_call(**kwargs):
    return dict(kwargs)


def tuple_call(*args):
    return tuple(args)
