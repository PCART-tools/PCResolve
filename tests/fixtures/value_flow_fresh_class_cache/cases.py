class Fresh:
    @classmethod
    def touch(cls):
        name = 'ca' + 'che'
        setattr(cls, name, {})
        return getattr(cls, name)

    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


class Direct(Fresh):
    @classmethod
    def touch(cls):
        cls.cache = []
        return cls.cache


class Probe(Fresh):
    @classmethod
    def touch(cls):
        name = 'cache'
        alias = cls
        setattr(alias, name, {})
        if hasattr(alias, name):
            return getattr(alias, name, None)


class BothBranches(Fresh):
    @classmethod
    def touch(cls, enabled=True):
        if enabled:
            name = 'cache'
            cls.cache = {}
        else:
            name = 'ca' + 'che'
            cls.cache = []
        return getattr(cls, name)


class RebindingDescriptor:
    def __get__(self, instance, owner):
        owner.fixed = staticmethod(lambda **kwargs: kwargs)
        return {}


class ReplacedDescriptor(Fresh):
    cache = RebindingDescriptor()


class ExistingDescriptor(Fresh):
    cache = RebindingDescriptor()

    @classmethod
    def touch(cls):
        return getattr(cls, 'cache')


class ConditionalDescriptor(ExistingDescriptor):
    @classmethod
    def touch(cls):
        if not hasattr(cls, 'cache'):
            setattr(cls, 'cache', {})
        return getattr(cls, 'cache')


class OneBranch(ExistingDescriptor):
    @classmethod
    def touch(cls, enabled=False):
        if enabled:
            cls.cache = {}
        return cls.cache


class UnknownValue(Fresh):
    @classmethod
    def touch(cls):
        cls.cache = RebindingDescriptor()
        return getattr(cls, 'cache')


class ReadBeforeWrite(ExistingDescriptor):
    @classmethod
    def touch(cls):
        getattr(cls, 'cache')
        cls.cache = {}


class Deleted(ExistingDescriptor):
    @classmethod
    def touch(cls):
        cls.cache = {}
        del cls.cache
        return getattr(cls, 'cache')


class ReboundName(Fresh):
    @classmethod
    def touch(cls):
        name = 'cache'
        name = 'fi' + 'xed'
        setattr(cls, name, staticmethod(lambda **kwargs: kwargs))


class DivergentName(Fresh):
    @classmethod
    def touch(cls, enabled=False):
        name = 'cache'
        if enabled:
            name = 'cache'
        else:
            name = 'fixed'
        setattr(cls, name, staticmethod(lambda **kwargs: kwargs))


class ShadowedGetattr(ExistingDescriptor):
    @classmethod
    def touch(cls):
        cls.cache = {}
        getattr = lambda owner, name: setattr(owner, 'fixed', staticmethod(lambda **kw: kw))
        return getattr(cls, 'cache')


class DynamicName(Fresh):
    @classmethod
    def touch(cls, name='fixed'):
        setattr(cls, name, staticmethod(lambda **kwargs: kwargs))


class LiteralPrivate(Fresh):
    @classmethod
    def touch(cls):
        name = '__cache'
        setattr(cls, name, {})
        return getattr(cls, name)


class SyntaxPrivate(Fresh):
    @classmethod
    def touch(cls):
        cls.__cache = {}
        return cls.__cache


class ComprehensionWrite(Fresh):
    @classmethod
    def touch(cls):
        cls.cache = {}
        [None for cls.cache in (RebindingDescriptor(),)]
        return cls.cache


class OverwrittenPayload(Fresh):
    @classmethod
    def touch(cls):
        cls.cache = {}
        cls.cache = RebindingDescriptor()
        return cls.cache


class DeferredRead(Fresh):
    @classmethod
    def touch(cls):
        cls.cache = {}
        reader = lambda: cls.cache
        cls.cache = RebindingDescriptor()
        return reader()


class ShadowedLiteralFactory(Fresh):
    @classmethod
    def touch(cls):
        set = RebindingDescriptor
        cls.cache = set()
        return cls.cache


def discarded(**kwargs):
    Fresh.touch()
    kwargs.clear()
    return Fresh.fixed(**kwargs)
