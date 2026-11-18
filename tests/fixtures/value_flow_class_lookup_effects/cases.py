from class_lookup_support import touch_other


class CacheOnly:
    @classmethod
    def touch(cls):
        cls.cache = {}

    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


class Inherited(CacheOnly):
    pass


class SetCache(CacheOnly):
    @classmethod
    def touch(cls):
        alias = cls
        setattr(alias, 'cache', {})


class Changed(CacheOnly):
    @classmethod
    def touch(cls):
        cls.fixed = staticmethod(lambda **kwargs: kwargs)


class Dynamic(CacheOnly):
    @classmethod
    def touch(cls):
        setattr(cls, unknown_name(), {})


class Exposed(CacheOnly):
    @classmethod
    def touch(cls):
        opaque(cls)


class Reflected(CacheOnly):
    @classmethod
    def touch(cls):
        cls.__dict__['fixed'] = unknown()


class WithRead(CacheOnly):
    @classmethod
    def touch(cls):
        cls.cache = factory()
        return getattr(cls, 'cache')


class Conditional(CacheOnly):
    @classmethod
    def touch(cls, enabled=True):
        if enabled:
            cls.cache = {}
        else:
            cls.other_cache = []


class Mangled(CacheOnly):
    @classmethod
    def touch(cls):
        cls.__cache = {}


def touch(receiver):
    receiver.cache = {}


def relay(receiver, options):
    return receiver.fixed(**options)


class Helper(CacheOnly):
    def __new__(cls, **kwargs):
        touch(cls)
        return relay(cls, kwargs)


class ChangedHelper(CacheOnly):
    def __new__(cls, **kwargs):
        cls.touch()
        return relay(cls, kwargs)

    @classmethod
    def touch(cls):
        cls.fixed = staticmethod(lambda **kwargs: kwargs)


def returning(receiver):
    return receiver


class ReturnAfterChange(Changed):
    def __new__(cls, **kwargs):
        cls.touch()
        other = returning(cls)
        return other.fixed(**kwargs)


def aliased(receiver, other):
    receiver.cache = {}
    opaque(other)


class Aliased(CacheOnly):
    def __new__(cls, **kwargs):
        aliased(cls, cls)
        return cls.fixed(**kwargs)


class Structural(CacheOnly):
    @classmethod
    def touch(cls):
        cls.__bases__ = unknown()


class ShadowedSetattr(CacheOnly):
    @classmethod
    def touch(cls):
        setattr = opaque
        setattr(cls, 'cache', {})


class ReboundAlias(CacheOnly):
    @classmethod
    def touch(cls):
        alias = cls
        cls = None
        alias.fixed = staticmethod(lambda **kwargs: kwargs)


class Private:
    @classmethod
    def __fixed(cls, allowed=0):
        return allowed

    @classmethod
    def touch(cls):
        cls.__fixed = staticmethod(lambda **kwargs: kwargs)

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.__fixed(**kwargs)


class ResetAfterChange(Changed):
    def __new__(cls, **kwargs):
        cls.touch()
        touch(cls)
        return cls.fixed(**kwargs)


class ArgumentChange(CacheOnly):
    @classmethod
    def forward(cls, token=None, **kwargs):
        return cls.fixed(**kwargs)

    @classmethod
    def touch(cls):
        cls.fixed = staticmethod(lambda **kwargs: kwargs)

    def __new__(cls, **kwargs):
        return cls.forward(token=cls.touch(), **kwargs)


class OtherHelper(CacheOnly):
    def __new__(cls, **kwargs):
        touch_other(cls)
        return cls.fixed(**kwargs)


class UncertainAlias(CacheOnly):
    def __new__(cls, other=None, **kwargs):
        aliased(cls, other)
        return cls.fixed(**kwargs)


class ClearsCarrier(CacheOnly):
    @classmethod
    def touch(cls, options):
        cls.cache = {}
        options.clear()

    def __new__(cls, **kwargs):
        cls.touch(kwargs)
        return cls.fixed(**kwargs)


def literal_cache(**kwargs):
    CacheOnly.touch()
    return CacheOnly.fixed(**kwargs)


def literal_changed(**kwargs):
    Changed.touch()
    return Changed.fixed(**kwargs)


class ReceiverCollision(CacheOnly):
    @classmethod
    def touch(cls, **options):
        cls.cache = {}

    def __new__(cls, **kwargs):
        cls.touch(cls=1)
        return cls.fixed(**kwargs)


class PosOnlyReceiver(CacheOnly):
    @classmethod
    def touch(cls, /, **options):
        cls.cache = {}

    def __new__(cls, **kwargs):
        cls.touch(cls=1)
        return cls.fixed(**kwargs)
