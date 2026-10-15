class Base:
    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


class Descriptor:
    def __get__(self, instance, owner):
        owner.fixed = staticmethod(lambda **kwargs: kwargs)
        return {}


class ____(Base):
    @classmethod
    def touch(cls):
        cls.__cache = {}
        return getattr(cls, '__cache')

    @classmethod
    def stored(cls):
        cls.__impl = Base
        return cls.__impl


class ___(Base):
    ___cache = Descriptor()

    @classmethod
    def touch(cls):
        cls.__cache = {}
        return getattr(cls, '___cache')


class _Named(Base):
    @classmethod
    def touch(cls):
        cls.__cache = {}
        return getattr(cls, '_Named__cache')
