def guarded(value):
    if isinstance(value, str):
        return value.split('.')
    return None


def unknown(value):
    return value.split('.')


def rebound(value, other):
    if isinstance(value, str):
        value = other
        return value.split('.')


def shadowed(value, isinstance):
    if isinstance(value, str):
        return value.split('.')
