class Trap:
    def __get__(self, instance, owner):
        owner.fixed = staticmethod(lambda **kwargs: kwargs)
        return {}


def unknown():
    return Trap()


class Base:
    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


class Local(Base):
    @classmethod
    def touch(cls):
        value = {}
        cls.cache = value
        return cls.cache


class Alias(Base):
    @classmethod
    def touch(cls):
        value = {}
        other = value
        setattr(cls, 'cache', other)
        return getattr(cls, 'cache')


class Annotated(Base):
    @classmethod
    def touch(cls):
        value: dict = {}
        other: dict = value
        cls.cache = other
        return cls.cache


class Branches(Base):
    @classmethod
    def touch(cls, enabled=True):
        if enabled:
            value = {}
        else:
            value = []
        cls.cache = value
        return cls.cache


class ReboundOriginal(Base):
    @classmethod
    def touch(cls):
        value = {}
        alias = value
        value = unknown()
        cls.cache = alias
        return cls.cache


class ReboundAfterWrite(Base):
    @classmethod
    def touch(cls):
        value = {}
        cls.cache = value
        value = unknown()
        return cls.cache


class Primitive(Base):
    @classmethod
    def touch(cls):
        value = None
        cls.cache = value
        return getattr(cls, 'cache')


class Metadata(Base):
    @classmethod
    def touch(cls):
        value = {}
        name = '_cache_' + cls.__name__
        setattr(cls, name, value)
        return getattr(cls, name)


class ConditionalRead(Base):
    @classmethod
    def touch(cls):
        value = {}
        cls.cache = value
        if not hasattr(cls, 'cache'):
            replacement = []
            cls.cache = replacement
        return getattr(cls, 'cache')


class Rebound(Base):
    @classmethod
    def touch(cls):
        value = {}
        value = unknown()
        cls.cache = value
        return cls.cache


class ReboundAlias(Base):
    @classmethod
    def touch(cls):
        value = {}
        alias = value
        alias = unknown()
        cls.cache = alias
        return cls.cache


class UnknownBranch(Base):
    @classmethod
    def touch(cls, enabled=False):
        if enabled:
            value = {}
        else:
            value = unknown()
        cls.cache = value
        return cls.cache


class MissingBranch(Base):
    @classmethod
    def touch(cls, enabled=False):
        if enabled:
            value = {}
        cls.cache = value
        return cls.cache


class ReplacedAttribute(Base):
    @classmethod
    def touch(cls):
        value = {}
        cls.cache = value
        cls.cache = unknown()
        return cls.cache


class ConditionalExisting(Base):
    @classmethod
    def touch(cls):
        value = {}
        if not hasattr(cls, 'cache'):
            cls.cache = value
        return cls.cache


class ParameterValue(Base):
    @classmethod
    def touch(cls, value=None):
        cls.cache = value
        return cls.cache


class UnknownFactory(Base):
    @classmethod
    def touch(cls):
        value = unknown()
        cls.cache = value
        return cls.cache


class ProtectedAlias(Base):
    @classmethod
    def touch(cls):
        value = {}
        value = cls
        cls.cache = value
        return cls.cache


class AnnotationOnly(Base):
    @classmethod
    def touch(cls):
        value = {}
        value: dict
        cls.cache = value
        return cls.cache


class Chained(Base):
    @classmethod
    def touch(cls):
        value = alias = {}
        cls.cache = value
        return cls.cache


class DeletedCache(Base):
    @classmethod
    def touch(cls):
        value = {}
        cls.cache = value
        del cls.cache
        return cls.cache


class BranchRebind(Base):
    @classmethod
    def touch(cls, enabled=True):
        value = {}
        if enabled:
            value = unknown()
        cls.cache = value
        return cls.cache
