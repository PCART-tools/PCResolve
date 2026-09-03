def pack(value):
    return [value]


def relay(value):
    return pack(value)


def strings():
    return [' alpha ']


def mixed(value, other):
    if other:
        return other
    return [value]


def recursive(value):
    return recursive(value)


class Producer:
    def pack(self, value):
        return [value]


class Value:
    def reshape(self, size):
        return self


def default_pack(value='text'):
    return [value]


def expanded(values):
    return [*values]


def conflicting(left, right, flag):
    if flag:
        return [left]
    return [right]


def generator(value):
    yield value


def generator_relay(value):
    return generator(value)
