## @package value_flow_class_contexts.hierarchy

from backends import BaseBackend


class Base:
    ## @return The source class selected by the generic base.
    @classmethod
    def default(cls):
        return BaseBackend

    ## Construct a returned source class and invoke its instance method.
    #  @param kwargs Values forwarded to the selected initializer.
    #  @return The initialization result.
    @classmethod
    def allocate(cls, **kwargs):
        implementation = cls.default()
        instance = implementation()
        return instance.initialize(**kwargs)


class Derived(Base):
    ## @return The source class selected by this subclass.
    @classmethod
    def default(cls):
        from backends import DerivedBackend
        return DerivedBackend

    ## @return The inherited allocation result with this class receiver.
    @classmethod
    def root(cls, **kwargs):
        return super(Derived, cls).allocate(**kwargs)


class Other(Base):
    ## @return A different source class selected by this subclass.
    @classmethod
    def default(cls):
        from backends import OtherBackend
        return OtherBackend

    ## @return The inherited allocation result with this other class receiver.
    @classmethod
    def root(cls, **kwargs):
        return super().allocate(**kwargs)


class UnknownBackend(Base):
    ## @return An unproven factory result.
    @classmethod
    def default(cls):
        return external_factory()

    ## @return An allocation whose implementation is unknown.
    @classmethod
    def root(cls, **kwargs):
        return super().allocate(**kwargs)


class Recursive(Base):
    ## @return A recursive class-return dependency without a finite proof.
    @classmethod
    def default(cls):
        return cls.default()

    ## @return An allocation with a recursive default-class source.
    @classmethod
    def root(cls, **kwargs):
        return super().allocate(**kwargs)


class UnknownReceiver(Base):
    ## @return A nominal inherited helper call after losing receiver evidence.
    @classmethod
    def root(cls, **kwargs):
        cls = external_factory()
        return super().allocate(**kwargs)


## @return Calls through two distinct subclass contexts.
def both(**kwargs):
    return Derived.root(**kwargs), Other.root(**kwargs)


## @return The known call followed by the unknown-receiver call.
def known_then_unknown(**kwargs):
    return Derived.root(**kwargs), UnknownReceiver.root(**kwargs)


## @return The unknown-receiver call followed by the known call.
def unknown_then_known(**kwargs):
    return UnknownReceiver.root(**kwargs), Derived.root(**kwargs)


## @return A call on an arbitrary, unproven class receiver.
def unknown_receiver(cls, **kwargs):
    return cls.allocate(**kwargs)


## @return One known class or an unknown parameter value.
def partial_type(flag, supplied):
    if flag:
        from backends import DerivedBackend
        return DerivedBackend
    return supplied


## @return An unproven call whose callee has a mixed return origin.
def partial_root(flag, supplied, **kwargs):
    implementation = partial_type(flag, supplied)
    instance = implementation()
    return instance.initialize(**kwargs)
