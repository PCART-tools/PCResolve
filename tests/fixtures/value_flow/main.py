from helper import convert
from helper import outer


def entry(arg, errors='raise', origin='unix'):
    if origin != 'unix':
        arg = arg + 1
    if origin == 'unix':
        result = convert(arg, errors=errors)
    else:
        result = None
    return result


def discarded(x):
    convert(x)
    return x


def repeated(x, y):
    a = convert(x)
    b = convert(y)
    return b


def through(x):
    return convert(x)


def rebound(x):
    convert = x
    return convert(x)


def nested(x):
    return convert(convert(x))


def deep(x):
    return outer(x)
