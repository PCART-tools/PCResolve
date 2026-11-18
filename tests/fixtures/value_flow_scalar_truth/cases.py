def convert(value):
    return bool(value)


def shadowed(bool, value):
    return bool(value)


def invalid(value):
    return bool(value, value)


def expanded(values):
    return bool(*values)


def rebound(value):
    result = bool(value)
    bool = external
    return result
