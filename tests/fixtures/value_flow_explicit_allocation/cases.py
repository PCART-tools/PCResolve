class Backend:
    def __new__(cls):
        return 'replaced'

    def initialize(self, allowed=0):
        return allowed


class Other:
    def initialize(self, other=0):
        return other


class Factory:
    implementation = None

    @classmethod
    def configured(cls):
        if cls.implementation is None:
            cls.implementation = Backend
        return cls.implementation

    @classmethod
    def conditional(cls, **kwargs):
        impl = cls.configured()
        instance = super(Factory, cls).__new__(impl)
        return instance.initialize(**kwargs)

    @classmethod
    def direct(cls, **kwargs):
        impl = cls.configured()
        instance = object.__new__(impl)
        return instance.initialize(**kwargs)

    @classmethod
    def mixed(cls, flag, **kwargs):
        if flag:
            impl = Backend
        else:
            impl = Other
        instance = super(Factory, cls).__new__(impl)
        return instance.initialize(**kwargs)

    @classmethod
    def shadowed(cls, super, **kwargs):
        instance = super(Factory, cls).__new__(Backend)
        return instance.initialize(**kwargs)


def bypass(**kwargs):
    instance = object.__new__(Backend)
    return instance.initialize(**kwargs)


def ordinary(**kwargs):
    instance = Backend()
    return instance.initialize(**kwargs)


def rebound(object, **kwargs):
    instance = object.__new__(Backend)
    return instance.initialize(**kwargs)


class SourceAllocator:
    def __new__(cls):
        return 'replaced'


class CustomFactory(SourceAllocator):
    @classmethod
    def allocate(cls, **kwargs):
        instance = super(CustomFactory, cls).__new__(cls)
        return instance.initialize(**kwargs)

    def initialize(self, allowed=0):
        return allowed


class Unknown(external_base):
    def initialize(self, allowed=0):
        return allowed


def unknown(**kwargs):
    instance = object.__new__(Unknown)
    return instance.initialize(**kwargs)


class DefinitionEffects:
    marker = unknown_factory()

    def initialize(self, allowed=0):
        return allowed


def definition_effects(**kwargs):
    instance = object.__new__(DefinitionEffects)
    return instance.initialize(**kwargs)


def partial_layout(flag, **kwargs):
    impl = Backend if flag else Unknown
    instance = object.__new__(impl)
    return instance.initialize(**kwargs)


class AssignedAllocator:
    __new__ = None


class AssignedFactory(AssignedAllocator):
    @classmethod
    def allocate(cls, **kwargs):
        instance = super(AssignedFactory, cls).__new__(Backend)
        return instance.initialize(**kwargs)


class PatchedAllocator:
    pass


class PatchedFactory(PatchedAllocator):
    @classmethod
    def allocate(cls, **kwargs):
        instance = super(PatchedFactory, cls).__new__(Backend)
        return instance.initialize(**kwargs)


PatchedAllocator.__new__ = SourceAllocator.__new__
