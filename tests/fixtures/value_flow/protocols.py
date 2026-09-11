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


def structural_partition(value):
    left, separator, right = value.partition(':')
    return left, right


def opaque_partition(value):
    return value.partition(':')


def generate_with_assignment(value):
    received = yield value
    return received


def consume_assigned_yield(value):
    return next(generate_with_assignment(value))
