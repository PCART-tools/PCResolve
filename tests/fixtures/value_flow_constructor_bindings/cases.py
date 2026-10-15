class FixedNew:
    def __new__(cls, **kwargs):
        return cls.fixed(**kwargs)

    @classmethod
    def fixed(cls, allowed=0):
        return allowed


class DerivedNew(FixedNew):
    pass


def direct(**kwargs):
    return FixedNew(**kwargs)


def inherited(**kwargs):
    return DerivedNew(**kwargs)


def relay(factory, mapping):
    return factory(**mapping)


def indirect(**kwargs):
    return relay(FixedNew, kwargs)


def unknown(factory, **kwargs):
    return factory(**kwargs)


class Meta(type):
    def __call__(cls, **kwargs):
        return kwargs


class Customized(metaclass=Meta):
    def __new__(cls, allowed=0):
        return allowed


def custom(**kwargs):
    return Customized(**kwargs)


class Patched:
    def __new__(cls, **kwargs):
        return cls.fixed(**kwargs)

    @classmethod
    def fixed(cls, allowed=0):
        return allowed


def replacement(cls, **kwargs):
    return kwargs


Patched.__new__ = replacement


def patched(**kwargs):
    return Patched(**kwargs)


def escaped(**kwargs):
    external(FixedNew)
    return FixedNew(**kwargs)


def captured_alias(factory, mapping):
    def mutate():
        external(factory)
    mutate()
    return factory(**mapping)


def captured(**kwargs):
    return captured_alias(FixedNew, kwargs)


class Both:
    def __new__(cls, **kwargs):
        return 1

    def __init__(self, **kwargs):
        pass


def both(**kwargs):
    return Both(**kwargs)


def collision(**kwargs):
    return FixedNew(cls=1, **kwargs)


def expanded_collision(**kwargs):
    return FixedNew(**{'cls': 1}, **kwargs)


class PosOnlyNew(FixedNew):
    def __new__(cls, /, **kwargs):
        return kwargs


def positional_only(**kwargs):
    return PosOnlyNew(cls=1, **kwargs)


def argument_escape(**kwargs):
    return FixedNew(dummy=external(FixedNew), **kwargs)


class StaticNew(FixedNew):
    @staticmethod
    def __new__(cls, **kwargs):
        return cls.fixed(**kwargs)


def explicit_static(**kwargs):
    return StaticNew(**kwargs)


def invalid_keys(**kwargs):
    return FixedNew(**{1: 1}, **kwargs)


class DeferredNew(FixedNew):
    def __new__(cls, **kwargs):
        yield cls.fixed(**kwargs)


def deferred(**kwargs):
    return DeferredNew(**kwargs)


def escaped_base(**kwargs):
    external(FixedNew)
    return DerivedNew(**kwargs)


class PositionalNew:
    def __new__(cls, *args):
        return cls.fixed(*args)

    @classmethod
    def fixed(cls, allowed=0):
        return allowed


def positional(*args):
    return PositionalNew(*args)
