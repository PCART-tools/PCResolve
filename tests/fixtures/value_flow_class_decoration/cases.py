def fixed(allowed=0):
    return allowed


def caches(cls):
    for name in ['cache', 'other_cache']:
        setattr(cls, name, {})
    return cls


def replaced(cls):
    class Other:
        def __init__(self, **kwargs):
            pass
    return Other


def escaped(cls):
    opaque(cls)
    return cls


def rebound(cls):
    cls = factory()
    return cls


def structural(cls):
    setattr(cls, '__init__', lambda self, **kwargs: None)
    return cls


def dynamic(cls):
    setattr(cls, name(), True)
    return cls


def conditional(cls):
    if unknown():
        return factory()
    return cls


@caches
class Public:
    def __init__(self, **kwargs):
        fixed(**kwargs)


class Derived(Public):
    pass


@replaced
class Replaced:
    def __init__(self, **kwargs):
        fixed(**kwargs)


@escaped
class Escaped:
    def __init__(self, **kwargs):
        fixed(**kwargs)


@rebound
class Rebound:
    def __init__(self, **kwargs):
        fixed(**kwargs)


@structural
class Structural:
    def __init__(self, **kwargs):
        fixed(**kwargs)


@dynamic
class Dynamic:
    def __init__(self, **kwargs):
        fixed(**kwargs)


@conditional
class Conditional:
    def __init__(self, **kwargs):
        fixed(**kwargs)


def client(**kwargs):
    return Public(**kwargs)


class Replace:
    def __get__(self, instance, owner):
        return lambda fn: (lambda **kwargs: kwargs)


def descriptor(cls):
    cls.wrap = Replace()
    return cls


@descriptor
class Document:
    def __call__(self, fn):
        return self.wrap(fn)


@Document()
def decorated(**kwargs):
    return fixed(**kwargs)
