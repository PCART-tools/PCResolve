from helper import convert


def guarded(x):
    try:
        x = x + 1
    except ValueError:
        raise
    return convert(x)


def cleanup(x, y):
    try:
        return convert(x)
    finally:
        return y


def prefix(x, y):
    value = x
    try:
        convert(x)
        value = y
    except Exception:
        return value
    return None


def otherwise(x, y):
    try:
        raise ValueError()
        x = y
    except ValueError:
        return x
    else:
        return y


def closure(x, errors):
    def inner(data):
        return errors
    return inner(x)


def lexical(x):
    def convert(data):
        return data
    return convert(x)


def opaque(x):
    value = convert(x)
    return external(value)


def caller(x):
    return discard(convert(x))


def discard(data):
    return 0


def final_assignment(x, y):
    try:
        value = x
    finally:
        value = y
    return value


def default_capture(x, y):
    def inner(data=x):
        return data
    x = y
    return inner()


def wrapped(x):
    from vendor import wrap
    return wrap(convert(x))


def matched(x, y):
    try:
        raise ValueError()
    except TypeError:
        return y
    except ValueError:
        return x


def completed_else(x, y):
    try:
        value = x
    except ValueError:
        value = y
    else:
        value = y
    return value


def before_definition(x):
    result = inner(x)
    def inner(data):
        return data
    return result


def finally_raises(x):
    try:
        return convert(x)
    finally:
        raise ValueError()


def local_import(x):
    from helper import convert as transform
    return transform(x)


def capture_rebound(x, y):
    def inner():
        return x
    x = y
    return inner()


def exception_hierarchy(x, y):
    try:
        raise BaseException()
    except Exception:
        return y
    except BaseException:
        return x
