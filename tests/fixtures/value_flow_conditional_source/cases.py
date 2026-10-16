import weakref


class Factory:
    implementation = None

    @classmethod
    def base(cls):
        return Client

    @classmethod
    def configured(cls):
        if cls.implementation is None:
            cls.implementation = Backend
        return cls.implementation

    def __new__(cls, **kwargs):
        base = cls.base()
        if cls is base:
            impl = cls.configured()
        else:
            impl = cls
        instance = super(Factory, cls).__new__(impl)
        instance.initialize(**kwargs)
        return instance


class Client(Factory):
    @classmethod
    def cache(cls):
        name = '_cache_' + cls.__name__
        if not hasattr(cls, name):
            setattr(cls, name, weakref.WeakKeyDictionary())
        return getattr(cls, name)

    def __new__(cls, key=None, force=False, **kwargs):
        if key in cls.cache() and not force:
            return cls.cache()[key]
        return super(Client, cls).__new__(cls, **kwargs)


class Backend(Client):
    def initialize(self, allowed=0):
        return allowed


class Changed(Client):
    @classmethod
    def cache(cls):
        cls.__bases__ = ()
        return {}


class ChangedByName(Client):
    @classmethod
    def cache(cls):
        name = '__new__'
        setattr(cls, name, lambda *args, **kwargs: None)
        return {}


class Rebound(Client):
    def __new__(cls, other=None, **kwargs):
        cls = other
        cls.cache()
        return super(Rebound, cls).__new__(cls, **kwargs)


class Unreachable(Client):
    def __new__(cls, **kwargs):
        cls.cache()
        if True:
            return None
        return super(Unreachable, cls).__new__(cls, **kwargs)


def generic(cls, **kwargs):
    cls.cache()
    return cls(**kwargs)
