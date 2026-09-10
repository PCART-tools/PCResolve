from helpers import choose, identity, push, Parent, async_push


def keywords(x, y):
    return choose(right=x, left=y)


def discarded(x):
    identity(x)
    return 0


def overwritten(x, y):
    result = identity(x)
    result = y
    return result


def control_only(x, y):
    if x:
        return y
    return 0


def unpack_keywords(x):
    return choose(**{'left': 0, 'right': x})


def comprehension(x):
    return [item for item in x]


def nested_alias(x):
    inner = []
    outer = [inner]
    inner.append(x)
    return outer


def external_mutation(x):
    values = []
    push(values, x)
    return values


def negative_index(x, y):
    return [x, y][-1]


def sliced(x, y):
    return [x, y][1:]


def rebound(x):
    fn = identity
    fn = lambda value: 0
    return fn(x)


class Child(Parent):
    def run(self, x):
        return self.convert(x)
def reverse_selection(x, y):
    return [x, y][::-1][0]


def out_of_bounds(x):
    return [x][-2]


def appended_index(x, y):
    values = [x]
    values.append(y)
    return values[-1]


def comprehension_constant(x):
    return [0 for item in x]


def comprehension_scope(x, y):
    item = y
    result = [item for item in x]
    return item


def nested_clear(x):
    inner = [x]
    outer = [inner]
    inner.clear()
    return outer


def rebound_container(x):
    inner = []
    outer = [inner]
    inner = [x]
    return outer


class Shadowed(Parent):
    convert = None

    def run(self, x):
        return self.convert(x)
def empty_comprehension(x):
    return [x for item in []]


def rejected_comprehension(x):
    return [item for item in x if False]

def unawaited_mutation(x):
    values = []
    async_push(values, x)
    return values
