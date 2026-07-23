def identity(value):
    return value


def relay(value):
    return identity(value)


def use_value(value):
    return value.reshape(1, -1)


def conflicting_use(value):
    return value.mean()


def uncalled_use(value):
    return value.reshape(1, -1)


def recursive_identity(value, depth):
    if depth:
        return recursive_identity(value, depth - 1)
    return value


class Holder:
    def __init__(self, value):
        self.value = value

    def expose(self):
        return self.value
