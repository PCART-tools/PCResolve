class Fixed:
    @classmethod
    def generate(cls, allowed=0):
        return allowed


class Other:
    @classmethod
    def generate(cls, **kwargs):
        return kwargs


def relay(receiver, mapping):
    return receiver.generate(**mapping)


def another(receiver, mapping):
    return relay(receiver, mapping)


def fixed_root(**kwargs):
    return another(Fixed, kwargs)


def other_root(**kwargs):
    return another(Other, kwargs)


def unknown_root(receiver, **kwargs):
    return another(receiver, kwargs)


def escaped(receiver, mapping):
    unknown(receiver)
    return receiver.generate(**mapping)


def escaped_root(**kwargs):
    return escaped(Fixed, kwargs)


def patched(receiver, mapping):
    receiver.generate = unknown
    return receiver.generate(**mapping)


def patched_root(**kwargs):
    return patched(Fixed, kwargs)


def mixed(flag, **kwargs):
    receiver = Fixed if flag else unknown
    return relay(receiver, kwargs)


def contexts(**kwargs):
    return another(Fixed, kwargs), another(Other, kwargs), another(unknown, kwargs)


class Nominal:
    @classmethod
    def wrapper(cls, **kwargs):
        return cls.generate(**kwargs)

    @classmethod
    def generate(cls, allowed=0):
        return allowed


def nominal_root(**kwargs):
    return Nominal.wrapper(**kwargs)


def deleted(receiver, mapping):
    del receiver.generate
    return receiver.generate(**mapping)


def deleted_root(**kwargs):
    return deleted(Fixed, kwargs)


def hidden_escape(receiver, mapping):
    box = [receiver]
    unknown(box)
    return receiver.generate(**mapping)


def hidden_escape_root(**kwargs):
    return hidden_escape(Fixed, kwargs)


def aliased(receiver, mapping):
    alias = receiver
    alias.generate = unknown
    return receiver.generate(**mapping)


def aliased_root(**kwargs):
    return aliased(Fixed, kwargs)


def local_alias(receiver, mapping):
    alias = receiver
    return alias.generate(**mapping)


def local_alias_root(**kwargs):
    return local_alias(Fixed, kwargs)


def reassigned(receiver, mapping):
    receiver = unknown
    return receiver.generate(**mapping)


def reassigned_root(**kwargs):
    return reassigned(Fixed, kwargs)


class Derived(Fixed):
    pass


def inherited_root(**kwargs):
    return another(Derived, kwargs)


def global_escape_root(**kwargs):
    unknown(Fixed)
    return relay(Fixed, kwargs)


class CustomMeta(type):
    def __getattribute__(cls, name):
        if name == 'generate':
            return lambda **kwargs: kwargs
        return super().__getattribute__(name)


class Customized(metaclass=CustomMeta):
    @classmethod
    def generate(cls, allowed=0):
        return allowed


def custom_lookup_root(**kwargs):
    return relay(Customized, kwargs)


class HookBackend:
    @classmethod
    def prepare(cls):
        cls.generate = lambda **kwargs: kwargs

    @classmethod
    def generate(cls, allowed=0):
        return allowed


def prepared(receiver, mapping):
    receiver.prepare()
    return receiver.generate(**mapping)


def prepared_root(**kwargs):
    return prepared(HookBackend, kwargs)


def captured_write(receiver, mapping):
    def mutate():
        receiver.generate = unknown
    mutate()
    return receiver.generate(**mapping)


def captured_write_root(**kwargs):
    return captured_write(Fixed, kwargs)


class InheritedBase:
    @classmethod
    def generate(cls, allowed=0):
        return allowed


class InheritedChild(InheritedBase):
    pass


def mutate_base(receiver):
    receiver.generate = classmethod(lambda cls, **kwargs: kwargs)


def escaped_base_root(**kwargs):
    mutate_base(InheritedBase)
    return relay(InheritedChild, kwargs)


def aliased_base_root(**kwargs):
    child = InheritedChild
    mutate_base(InheritedBase)
    return relay(child, kwargs)
