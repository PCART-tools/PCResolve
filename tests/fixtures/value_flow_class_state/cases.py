class Backend:
    def initialize(self, allowed=0):
        return allowed


class Other:
    def initialize(self, other=0):
        return other


class Configurable:
    implementation = None

    @classmethod
    def default(cls):
        return Backend

    @classmethod
    def configured(cls):
        if cls.implementation is None:
            cls.implementation = cls.default()
        return cls.implementation

    @classmethod
    def allocate(cls, **kwargs):
        impl = cls.configured()
        instance = object.__new__(impl)
        return instance.initialize(**kwargs)

    @classmethod
    def known_branch(cls, flag):
        if flag:
            cls.implementation = Backend
            return cls.implementation
        return unknown_factory()

    @classmethod
    def direct_write(cls, **kwargs):
        cls.implementation = Backend
        instance = object.__new__(cls.implementation)
        return instance.initialize(**kwargs)

    @classmethod
    def overwrite(cls, **kwargs):
        cls.implementation = Backend
        cls.implementation = unknown_parameter
        instance = object.__new__(cls.implementation)
        return instance.initialize(**kwargs)

    @classmethod
    def escape(cls, **kwargs):
        cls.implementation = Backend
        unknown_effect(cls)
        instance = object.__new__(cls.implementation)
        return instance.initialize(**kwargs)

    @classmethod
    def mixed(cls, flag, **kwargs):
        if flag:
            cls.implementation = Backend
        else:
            cls.implementation = Other
        instance = object.__new__(cls.implementation)
        return instance.initialize(**kwargs)

    @classmethod
    def constructor(cls, **kwargs):
        impl = cls.configured()
        instance = impl()
        return instance.initialize(**kwargs)

    @classmethod
    def patched(cls, **kwargs):
        cls.default = unknown_function
        return cls.default(**kwargs)


class Derived(Configurable):
    @classmethod
    def default(cls):
        return Other


def root(**kwargs):
    return Configurable.allocate(**kwargs)


def derived(**kwargs):
    return Derived.allocate(**kwargs)


def generic(cls, **kwargs):
    cls.implementation = Backend
    return object.__new__(cls.implementation).initialize(**kwargs)


def rebound(**kwargs):
    object = unknown_allocator
    return object.__new__(Backend).initialize(**kwargs)


class Custom:
    def __new__(cls):
        return unknown_factory()

    def initialize(self, allowed=0):
        return allowed


class CustomState:
    @classmethod
    def root(cls, **kwargs):
        cls.implementation = Custom
        return cls.implementation().initialize(**kwargs)


def known(**kwargs):
    impl = Configurable.known_branch(True)
    return object.__new__(impl).initialize(**kwargs)
