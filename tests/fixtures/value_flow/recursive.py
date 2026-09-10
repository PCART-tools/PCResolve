def rotate(a, b, c, stop):
    if stop:
        return a
    return rotate(b, c, a, stop)


def no_return(a):
    return no_return(a)


def wrap(a, b):
    return a, b


def nested(a, b):
    return [wrap(a, b)]


def select(a, b):
    return nested(a, b)[0][1]
def growing(value, stop):
    if stop:
        return value
    return [growing(value, stop)]
