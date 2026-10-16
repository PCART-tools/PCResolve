class CacheDescriptor:
    def __get__(self, instance, owner):
        owner.fixed = staticmethod(lambda **kwargs: kwargs)
        return {}


def payload_factory():
    return CacheDescriptor()


class Fresh:
    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    @classmethod
    def cache_value(cls):
        if not hasattr(cls, 'cache'):
            setattr(cls, 'cache', {})
        return getattr(cls, 'cache')

    def __new__(cls, **kwargs):
        cls.cache_value()
        return cls.fixed(**kwargs)


class Preloaded(Fresh):
    cache = {}


class Descriptor(Fresh):
    cache = CacheDescriptor()


class UnknownFactory(Fresh):
    @classmethod
    def cache_value(cls):
        if not hasattr(cls, 'cache'):
            setattr(cls, 'cache', payload_factory())
        return getattr(cls, 'cache')


class Inherited(Preloaded):
    pass


class PositiveGuard(Fresh):
    @classmethod
    def cache_value(cls):
        if hasattr(cls, 'cache'):
            pass
        else:
            cls.cache = []
        return cls.cache


class Alias(Fresh):
    @classmethod
    def cache_value(cls):
        other = cls
        name = 'cache'
        if not hasattr(other, name):
            setattr(other, name, {})
        return getattr(other, name)


class ReadOnly(Fresh):
    @classmethod
    def cache_value(cls):
        return hasattr(cls, 'cache')


class InheritedDescriptor(Descriptor):
    pass


class LaterReplace(Fresh):
    @classmethod
    def mutate(cls):
        cls.cache = CacheDescriptor()


class DynamicSet(Fresh):
    @classmethod
    def mutate(cls, name, value):
        setattr(cls, name, value)


class AliasSetter(Fresh):
    @classmethod
    def mutate(cls):
        setter = setattr
        setter(cls, 'cache', CacheDescriptor())


class Written(Fresh):
    pass


Written.cache = CacheDescriptor()


class ReplacedBeforeRead(Fresh):
    @classmethod
    def cache_value(cls):
        cls.cache = CacheDescriptor()
        if not hasattr(cls, 'cache'):
            cls.cache = {}
        return cls.cache


class DeletedBeforeRead(Fresh):
    @classmethod
    def cache_value(cls):
        if not hasattr(cls, 'cache'):
            cls.cache = {}
        del cls.cache
        return cls.cache


class DirectRead(Preloaded):
    @classmethod
    def cache_value(cls):
        return cls.cache


class ShadowedHasattr(Fresh):
    @classmethod
    def cache_value(cls):
        hasattr = lambda owner, name: False
        if not hasattr(cls, 'cache'):
            cls.cache = {}
        return cls.cache


class Escaped(Fresh):
    pass


def mutate(owner):
    owner.cache = CacheDescriptor()


mutate(Escaped)


class PrivateDescriptor(Fresh):
    __cache = CacheDescriptor()

    @classmethod
    def cache_value(cls):
        if not hasattr(cls, '_PrivateDescriptor__cache'):
            cls.__cache = {}
        return cls.__cache


class PrivatePlain(Fresh):
    __cache = {}

    @classmethod
    def cache_value(cls):
        if not hasattr(cls, '_PrivatePlain__cache'):
            cls.__cache = {}
        return cls.__cache


class ReplacedMethod(Fresh):
    @classmethod
    def mutate(cls):
        cls.cache = {}


ReplacedMethod.mutate = classmethod(lambda cls: setattr(cls, 'cache', CacheDescriptor()))


class StructuralWriter(Fresh):
    @classmethod
    def mutate(cls):
        cls.cache_value = classmethod(lambda cls: setattr(cls, 'cache', CacheDescriptor()))


class MethodEscape(Fresh):
    @classmethod
    def install(cls):
        mutate(cls)


class MethodAliasEscape(Fresh):
    @classmethod
    def install(cls):
        owner = cls
        box = [owner]
        mutate(box[0])


class MethodReturnEscape(Fresh):
    @classmethod
    def owner(cls):
        return cls


class MethodClosureEscape(Fresh):
    @classmethod
    def install(cls):
        def deferred():
            mutate(cls)
        deferred()


class MethodDescriptorRead(Fresh):
    trigger = CacheDescriptor()

    @classmethod
    def install(cls):
        cls.trigger


def install_indirect_caches():
    MethodEscape.install()
    MethodAliasEscape.install()
    mutate(MethodReturnEscape.owner())
    MethodClosureEscape.install()


install_indirect_caches()


class NamespaceMethodReplacement(Fresh):
    cache_value = CacheDescriptor()


class SiblingInvalidatesRead(Fresh):
    @classmethod
    def install(cls):
        cls.other = CacheDescriptor()

    @classmethod
    def cache_value(cls):
        cls.other = {}
        cls.install()
        if not hasattr(cls, 'cache'):
            cls.cache = {}
        return cls.other
