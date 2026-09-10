def conditional(flag, x, y):
    return x if flag else y


def unpack(values):
    left, right = values
    return right


def loop(items):
    result = None
    for item in items:
        result = item
    return result


def uncovered(x):
    with x:
        print(x)


def converted(x):
    return str(x)


def literal_unpack(x, y):
    left, right = (x, y)
    return right


class Worker:
    def entry(self, value):
        return self.identity(value)

    def identity(self, data):
        return data
