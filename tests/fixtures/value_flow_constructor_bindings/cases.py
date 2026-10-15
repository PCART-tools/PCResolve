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


class SkipsInit:
    def __new__(cls, **kwargs):
        return 1

    def __init__(self, allowed=0):
        raise AssertionError('initialization must not execute')


def skips_init(**kwargs):
    return SkipsInit(**kwargs)


class InheritedSkip(SkipsInit):
    def __init__(self, allowed=0):
        raise AssertionError('initialization must not execute')


def inherited_skip(**kwargs):
    return InheritedSkip(**kwargs)


class Allocates(FixedNew):
    def __init__(self, allowed=0):
        raise AssertionError('initialization must not execute')


def inherited_new(**kwargs):
    return Allocates(**kwargs)


class FixedAllocator:
    def __new__(cls, allowed=0):
        return allowed

    def __init__(self, **kwargs):
        raise AssertionError('initialization must not execute')


def fixed_allocator(**kwargs):
    return FixedAllocator(**kwargs)


class OrdinaryInit:
    def __init__(self, allowed=0):
        self.allowed = allowed


class InheritedInit(OrdinaryInit):
    pass


def ordinary_init(**kwargs):
    return OrdinaryInit(**kwargs)


def inherited_init(**kwargs):
    return InheritedInit(**kwargs)


class CustomizedInit(metaclass=Meta):
    def __init__(self, allowed=0):
        raise AssertionError('metaclass bypasses initialization')


def custom_init(**kwargs):
    return CustomizedInit(**kwargs)


class AssignedNew:
    __new__ = staticmethod(lambda cls, **kwargs: 1)

    def __init__(self, allowed=0):
        raise AssertionError('initialization must not execute')


def assigned_new(**kwargs):
    return AssignedNew(**kwargs)


class ReboundNew:
    def __init__(self, allowed=0):
        raise AssertionError('initialization must not execute')


ReboundNew.__new__ = staticmethod(lambda cls, **kwargs: 1)


def rebound_new(**kwargs):
    return ReboundNew(**kwargs)


class InheritedRebound(ReboundNew):
    pass


def inherited_rebound(**kwargs):
    return InheritedRebound(**kwargs)


class NeedsInit:
    def __new__(cls, **kwargs):
        return object.__new__(cls)

    def __init__(self, allowed=0):
        self.allowed = allowed


def needs_init(**kwargs):
    return NeedsInit(**kwargs)


class AllocationHook:
    def __init_subclass__(cls):
        cls.__new__ = staticmethod(lambda cls, **kwargs: 1)


class HookedInit(AllocationHook):
    def __init__(self, allowed=0):
        raise AssertionError('initialization must not execute')


def hooked_init(**kwargs):
    return HookedInit(**kwargs)


class CustomDescriptorNew:
    @classmethod
    def __new__(cls, **kwargs):
        return cls.fixed(**kwargs)

    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    def __init__(self, **kwargs):
        pass


def custom_descriptor(**kwargs):
    return CustomDescriptorNew(**kwargs)
