def inner(value):
    yield value


def outer(value):
    yield from inner(value)
