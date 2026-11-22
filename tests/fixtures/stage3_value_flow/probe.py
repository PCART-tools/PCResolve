def sink(data, index, columns, dtype=None):
    return data


def convert(data):
    return data


def frame(data, index, columns, mode, named, nonempty, nested):
    if mode == 1:
        if data.dtype.names:
            columns = list(data.dtype.names)
            data = dict(data)
            return sink(data, index, columns)
        elif named:
            return sink(data, index, columns)
        else:
            return sink(data, index, columns)
    elif mode == 2:
        if nonempty:
            if nested:
                columns = convert(columns)
                index = convert(index)
                return sink(data, index, columns)
            else:
                return sink(data, index, columns)
        else:
            return sink({}, index, columns)
    else:
        values = convert(data)
        return sink(values, index, columns, dtype=values.dtype)


def predicate(arr):
    return bool(arr)


def common_type(types):
    has_bools = any(predicate(t) for t in types)
    if has_bools:
        return object
    return float


class Index:
    def tolist(self):
        if predicate(self):
            return [object()]
        return [0]

    def indexed_same(self, other):
        return all([self.axis(a).equals(other.axis(a)) for a in self.axes])

    def axis(self, a):
        return self.axes[a]


class Manager:
    def apply(self, consolidate, data):
        if consolidate:
            self.consolidate(data)
        for item in self.blocks:
            sink(item, None, None)

    def consolidate(self, data):
        if data:
            self.blocks = data


class Fixed:
    def update(self, value):
        self.set_version(value)

    def set_version(self, value):
        self.version = value


class StringMethods:
    def split(self, sep):
        return sep


def offset(name):
    return name.split('-')


def common_type_nested(types, has_numeric):
    has_bools = any(predicate(t) for t in types)
    if has_bools:
        if has_numeric:
            return object
    return float
