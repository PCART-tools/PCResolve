def carried(x, items):
    a = None
    b = None
    for item in items:
        sink(a)
        a = b
        b = x
    return a


def breaks(x, y, items):
    value = x
    for item in items:
        value = y
        break
    else:
        return x
    return value


def continued(x, y, items):
    value = x
    for item in items:
        continue
        value = y
    return value


def growing(x, items):
    for item in items:
        x = x.field
    return x


def projection_growth(x, items):
    for item in items:
        x, unused = x
    return x
