## @package cases
#  Class values require proven class identity and conservative allocation.

import provider as engines
from provider import External as Remote
from rebound import select as select_rebound
from unstable_imports import select_alias as select_rebound_alias
from unstable_imports import select_module as select_rebound_module
from changed_namespace import select as select_changed_namespace
from custom_descriptors import select_class as select_custom_classmethod
from custom_descriptors import select_static as select_custom_staticmethod


class Client:
    def __init__(self):
        pass

    def initialize(self, **kwargs):
        return kwargs


class Other:
    def __init__(self):
        pass

    def initialize(self, **kwargs):
        return kwargs


ClientAlias = Client


def select_same():
    return Client


def select_module_alias():
    return ClientAlias


def select_local_alias():
    implementation = Client
    return implementation


def select_imported():
    return Remote


def select_module_attribute():
    return engines.External


def select_local_import():
    from provider import External as Implementation
    return Implementation


def select_nested():
    class Nested:
        def __init__(self):
            pass

        def initialize(self, **kwargs):
            return kwargs

    return Nested


def same_module(**kwargs):
    impl = select_same()
    instance = impl()
    return instance.initialize(**kwargs)


def module_alias(**kwargs):
    impl = select_module_alias()
    instance = impl()
    return instance.initialize(**kwargs)


def local_alias(**kwargs):
    impl = select_local_alias()
    instance = impl()
    return instance.initialize(**kwargs)


def imported(**kwargs):
    impl = select_imported()
    instance = impl()
    return instance.initialize(**kwargs)


def module_attribute(**kwargs):
    impl = select_module_attribute()
    instance = impl()
    return instance.initialize(**kwargs)


def local_import(**kwargs):
    impl = select_local_import()
    instance = impl()
    return instance.initialize(**kwargs)


def nested(**kwargs):
    impl = select_nested()
    instance = impl()
    return instance.initialize(**kwargs)


def instance_alias(**kwargs):
    impl = select_same()
    instance = impl()
    initialized = instance
    return initialized.initialize(**kwargs)


def class_unbound_method(receiver, **kwargs):
    implementation = Client
    return implementation.initialize(receiver, **kwargs)


def allocated_object(**kwargs):
    impl = select_same()
    instance = object.__new__(impl)
    return instance.initialize(**kwargs)


def allocated_object_extra(extra, **kwargs):
    impl = select_same()
    instance = object.__new__(impl, extra)
    return instance.initialize(**kwargs)


def allocated_object_keyword(extra, **kwargs):
    impl = select_same()
    instance = object.__new__(impl, extra=extra)
    return instance.initialize(**kwargs)


class Allocator:
    @classmethod
    def create(cls, **kwargs):
        impl = select_backend()
        instance = super(Allocator, impl).__new__(impl)
        return instance.initialize(**kwargs)

    @classmethod
    def shadowed_super(cls, super, **kwargs):
        impl = select_backend()
        instance = super(Allocator, impl).__new__(impl)
        return instance.initialize(**kwargs)

    @classmethod
    def shadowed_current_class(cls, Allocator, **kwargs):
        impl = select_backend()
        instance = super(Allocator, impl).__new__(impl)
        return instance.initialize(**kwargs)

    @classmethod
    def rebound_current_class(cls, replacement, **kwargs):
        Allocator = replacement
        impl = select_backend()
        instance = super(Allocator, impl).__new__(impl)
        return instance.initialize(**kwargs)

    @classmethod
    def extra_argument(cls, extra, **kwargs):
        impl = select_backend()
        instance = super(Allocator, impl).__new__(impl, extra)
        return instance.initialize(**kwargs)

    @classmethod
    def keyword_argument(cls, extra, **kwargs):
        impl = select_backend()
        instance = super(Allocator, impl).__new__(impl, extra=extra)
        return instance.initialize(**kwargs)


class Backend(Allocator):
    def __init__(self):
        pass

    def initialize(self, **kwargs):
        return kwargs


def select_backend():
    return Backend


def select_unknown():
    return unknown_backend()


def unknown_backend_result(**kwargs):
    impl = select_unknown()
    instance = impl()
    return instance.initialize(**kwargs)


def identity(value):
    return value


def unknown_parameter(implementation, **kwargs):
    impl = identity(implementation)
    instance = impl()
    return instance.initialize(**kwargs)


def known_parameter_forwarding(**kwargs):
    impl = identity(Client)
    instance = impl()
    return instance.initialize(**kwargs)


def select_optional(flag):
    return Client if flag else None


def optional_class(flag, **kwargs):
    impl = select_optional(flag)
    instance = impl()
    return instance.initialize(**kwargs)


def select_fallthrough(flag):
    if flag:
        return Client


def fallthrough_class(flag, **kwargs):
    impl = select_fallthrough(flag)
    instance = impl()
    return instance.initialize(**kwargs)


def select_multiple(flag):
    if flag:
        return Client
    return Other


def multiple_candidates(flag, **kwargs):
    impl = select_multiple(flag)
    instance = impl()
    return instance.initialize(**kwargs)


def rebound_class(**kwargs):
    impl = select_rebound()
    instance = impl()
    return instance.initialize(**kwargs)


def rebound_imported_alias(**kwargs):
    impl = select_rebound_alias()
    instance = impl()
    return instance.initialize(**kwargs)


def rebound_module_alias(**kwargs):
    impl = select_rebound_module()
    instance = impl()
    return instance.initialize(**kwargs)


def changed_module_namespace(**kwargs):
    impl = select_changed_namespace()
    instance = impl()
    return instance.initialize(**kwargs)


def rebound_impl(replacement, **kwargs):
    impl = select_same()
    impl = replacement
    instance = impl()
    return instance.initialize(**kwargs)


def receiver_class_modified(**kwargs):
    impl = select_same()
    instance = impl()
    instance.__class__ = Other
    return instance.initialize(**kwargs)


def derived_class_receiver(**kwargs):
    instance = Client == None
    return instance.initialize(**kwargs)


def derived_instance_receiver(**kwargs):
    impl = select_same()
    instance = impl()
    instance = instance == None
    return instance.initialize(**kwargs)


def projected_instance_receiver(**kwargs):
    impl = select_same()
    instance = impl()
    instance = instance['feature']
    return instance.initialize(**kwargs)


def deleted_class_value(**kwargs):
    impl = select_same()
    del impl
    instance = impl()
    return instance.initialize(**kwargs)


def deleted_instance_value(**kwargs):
    impl = select_same()
    instance = impl()
    del instance
    return instance.initialize(**kwargs)


def rebound_object(object, **kwargs):
    impl = select_same()
    instance = object.__new__(impl)
    return instance.initialize(**kwargs)


class ChangingMeta(type):
    def __call__(cls):
        return Other()


class MetaChanged(metaclass=ChangingMeta):
    def __init__(self):
        pass

    def initialize(self, **kwargs):
        return kwargs


def select_metaclass():
    return MetaChanged


def custom_metaclass(**kwargs):
    impl = select_metaclass()
    instance = impl()
    return instance.initialize(**kwargs)


def custom_class_descriptor(**kwargs):
    impl = select_custom_classmethod()
    instance = impl()
    return instance.initialize(**kwargs)


def custom_static_descriptor(**kwargs):
    impl = select_custom_staticmethod()
    instance = impl()
    return instance.initialize(**kwargs)


class NewChanged:
    def __new__(cls):
        return Other()

    def __init__(self):
        pass

    def initialize(self, **kwargs):
        return kwargs


def select_custom_new():
    return NewChanged


def custom_new(**kwargs):
    impl = select_custom_new()
    instance = impl()
    return instance.initialize(**kwargs)


class UnknownMRO(external_base):
    def __init__(self):
        pass

    def initialize(self, **kwargs):
        return kwargs


def select_unknown_mro():
    return UnknownMRO


def unknown_mro(**kwargs):
    impl = select_unknown_mro()
    instance = impl()
    return instance.initialize(**kwargs)


def allocated_unknown_object(**kwargs):
    impl = select_unknown_mro()
    instance = object.__new__(impl)
    return instance.initialize(**kwargs)


class UnknownAllocator(external_base):
    @classmethod
    def create(cls, **kwargs):
        impl = select_unknown_allocated()
        instance = super(UnknownAllocator, impl).__new__(impl)
        return instance.initialize(**kwargs)


class UnknownAllocated(UnknownAllocator):
    def initialize(self, **kwargs):
        return kwargs


def select_unknown_allocated():
    return UnknownAllocated


def mapping_update(value, **kwargs):
    impl = select_same()
    instance = impl()
    kwargs.update({'added': value})
    return instance.initialize(**kwargs)


def mapping_clear(**kwargs):
    impl = select_same()
    instance = impl()
    kwargs.clear()
    return instance.initialize(**kwargs)


def finite_mapping(flag, **kwargs):
    impl = select_same()
    instance = impl()
    if flag:
        options = {'first': kwargs['first']}
    else:
        options = {'second': kwargs['second']}
    return instance.initialize(**options)


class ContextAllocator:
    @classmethod
    def allocate(cls, **kwargs):
        instance = object.__new__(cls)
        return instance.initialize(**kwargs)


class ContextKnown(ContextAllocator):
    def initialize(self, **kwargs):
        return kwargs


class ContextCustomNew(ContextAllocator):
    def __new__(cls):
        return Other()

    def initialize(self, **kwargs):
        return kwargs


def mixed_allocator_contexts(**kwargs):
    return ContextKnown.allocate(**kwargs), ContextCustomNew.allocate(**kwargs)
