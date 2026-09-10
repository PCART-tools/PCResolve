class Mapper:
    def resolve(self, name):
        return name


class Owner:
    def __init__(self):
        self.mapper = Mapper()

    def run(self, name):
        return self.mapper.resolve(name)


class Changed:
    def __init__(self):
        self.mapper = Mapper()

    def replace(self, other):
        self.mapper = other

    def run(self, name):
        return self.mapper.resolve(name)


def appended(x):
    values = []
    alias = values
    alias.append(x)
    return values


def cleared(x):
    values = [x]
    values.clear()
    return values


def dictionary(x, y):
    values = {'x': x, 'y': y}
    return values.get('x')


def pair(x, y):
    return x, y


def second(x, y):
    a, b = pair(x, y)
    return b


def local_selection(x, y):
    values = [x, y]
    return values[1]


def appended_return(x):
    values = []
    result = values.append(x)
    return result


def known_default(x, y):
    values = {'key': x}
    return values.get('key', y)


def joined(x):
    values = []
    values.append(x)
    return ','.join(values)


def short_circuit(x):
    return isinstance(x, str) and x.startswith('a')


def indirect_pair(x, y):
    return pair(x, y)


def indirect_second(x, y):
    return indirect_pair(x, y)[1]


def conditional_clear(x, y, flag):
    a = [x]
    b = [y]
    selected = a if flag else b
    selected.clear()
    return a


def dict_write(x, y):
    values = {'key': x}
    values['key'] = y
    return values.get('key')


def duplicate_key(x, y):
    return {'key': x, 'key': y}['key']


def branch_default(x, y, flag):
    values = {'key': x}
    if flag:
        values.clear()
    return values.get('key', y)
def conditional_append(x, flag):
    values = []
    flag and values.append(x)
    return values


def conditional_expression_clear(x, flag):
    values = [x]
    values.clear() if flag else None
    return values


def unconditional_short_circuit_clear(x, flag):
    values = [x]
    values.clear() or flag
    return values
def finally_append(x):
    values = []
    try:
        return values
    finally:
        values.append(x)


def finally_rebind(x, y):
    values = [x]
    try:
        return values
    finally:
        values = [y]


def finally_clear(x):
    values = [x]
    try:
        return values
    finally:
        values.clear()

def loop_default(x, y, items):
    values = {'key': x}
    result = None
    for item in items:
        result = values.get('key', y)
        values.clear()
    return result
