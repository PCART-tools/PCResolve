class Base:
    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    @classmethod
    def touch(cls, name):
        key = name + '_value'
        setattr(cls, key, {})
        return getattr(cls, key)


class Positional(Base):
    def __new__(cls, **kwargs):
        cls.touch('cache')
        return cls.fixed(**kwargs)


class Keyword(Base):
    def __new__(cls, **kwargs):
        cls.touch(name='cache')
        return cls.fixed(**kwargs)


class Local(Base):
    def __new__(cls, **kwargs):
        name = 'cache'
        cls.touch(name)
        return cls.fixed(**kwargs)


class KeywordOnly(Base):
    @classmethod
    def touch(cls, *, name):
        setattr(cls, name, {})
        return getattr(cls, name)

    def __new__(cls, **kwargs):
        cls.touch(name='cache')
        return cls.fixed(**kwargs)


def install(receiver, name):
    setattr(receiver, name, staticmethod(lambda **kwargs: kwargs))


class Helper(Base):
    def __new__(cls, **kwargs):
        install(cls, 'cache')
        return cls.fixed(**kwargs)


class Changed(Base):
    def __new__(cls, **kwargs):
        install(cls, 'fixed')
        return cls.fixed(**kwargs)


class Uncertain(Base):
    def __new__(cls, name='cache', **kwargs):
        install(cls, name)
        return cls.fixed(**kwargs)


class Divergent(Base):
    def __new__(cls, enabled=False, **kwargs):
        if enabled:
            name = 'cache'
        else:
            name = 'fixed'
        install(cls, name)
        return cls.fixed(**kwargs)


class Default(Base):
    @classmethod
    def touch(cls, name='cache'):
        setattr(cls, name, {})

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


class ReboundInput(Base):
    @classmethod
    def touch(cls, name):
        name = 'fixed'
        setattr(cls, name, staticmethod(lambda **kwargs: kwargs))

    def __new__(cls, **kwargs):
        cls.touch('cache')
        return cls.fixed(**kwargs)


class DuplicateInput(Base):
    def __new__(cls, **kwargs):
        cls.touch('cache', name='fixed')
        return cls.fixed(**kwargs)


class Name(str):
    def __radd__(self, prefix):
        return 'fixed'


class Metadata(Base):
    @classmethod
    def touch(cls):
        name = '_cache_' + cls.__name__
        setattr(cls, name, staticmethod(lambda **kwargs: kwargs))

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


Metadata.__name__ = Name('Metadata')


def clean(**kwargs):
    install(Base, 'cache')
    return Base.fixed(**kwargs)


def changed(**kwargs):
    install(Base, 'fixed')
    return Base.fixed(**kwargs)
