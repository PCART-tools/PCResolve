def choose(left, right, *, enabled=True):
    return right


def identity(value):
    return value


def push(values, value):
    values.append(value)


class Parent:
    def convert(self, value):
        return value
async def async_push(values, value):
    values.append(value)
