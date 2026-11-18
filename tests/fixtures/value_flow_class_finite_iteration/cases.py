class Base:
    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


class Aliases(Base):
    @classmethod
    def touch(cls):
        for prefix in ['get_', 'set_']:
            for alias in ['lw', 'ec']:
                setattr(cls, prefix + alias, True)


class Changed(Base):
    @classmethod
    def touch(cls):
        for name in ['cache', 'fixed']:
            setattr(cls, name, staticmethod(lambda **kwargs: kwargs))


class Unknown(Base):
    @classmethod
    def touch(cls):
        for name in names():
            setattr(cls, name, True)


class Empty(Base):
    @classmethod
    def touch(cls):
        for name in []:
            opaque(cls)
        else:
            cls.cache = True


class Escaped(Base):
    @classmethod
    def touch(cls):
        for name in ['cache']:
            opaque(cls)


class BranchChanged(Base):
    @classmethod
    def touch(cls):
        for name in ['cache']:
            if cls.__name__:
                name = 'fixed'
            else:
                name = 'cache'
            setattr(cls, name, staticmethod(lambda **kwargs: kwargs))
