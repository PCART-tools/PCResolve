class Backend:
    @classmethod
    def generate(cls, start=None):
        return start


class Derived(Backend):
    pass


class Override(Backend):
    @classmethod
    def generate(cls, start=None):
        return start


Alias = Backend


class Patched:
    @classmethod
    def generate(cls, start=None):
        return start


class Reflected:
    @classmethod
    def generate(cls, start=None):
        return start


class Escaped:
    @classmethod
    def generate(cls, start=None):
        return start


class Meta(type):
    def __getattribute__(cls, name):
        return unknown_descriptor(name)


class CustomMeta(metaclass=Meta):
    @classmethod
    def generate(cls, start=None):
        return start


def extra(function):
    return unknown_wrapper(function)


class Decorated:
    @extra
    @classmethod
    def generate(cls, start=None):
        return start


class Descriptor:
    def __get__(self, instance, owner):
        return unknown_callable


class DescriptorChild(Backend):
    generate = Descriptor()


class Shadowed:
    classmethod = extra

    @classmethod
    def generate(cls, start=None):
        return start


class Conditional:
    @classmethod
    def generate(cls, start=None):
        return start

    if unknown_flag:
        generate = unknown_callable


def factory():
    return Backend


def relay(**kwargs):
    return Backend.generate(**kwargs)


class Indirect:
    @classmethod
    def generate(cls, start=None):
        return start


class GlobalWrite:
    @classmethod
    def generate(cls, start=None):
        return start


class Deleted:
    @classmethod
    def generate(cls, start=None):
        return start


class CodeWrite:
    @classmethod
    def generate(cls, start=None):
        return start


class BuiltinAliasWrite:
    @classmethod
    def generate(cls, start=None):
        return start


class BranchWrite:
    @classmethod
    def generate(cls, start=None):
        return start


class BranchOther:
    @classmethod
    def generate(cls, start=None):
        return start


class HookBase:
    def __init_subclass__(cls):
        cls.generate = unknown_callable


class HookChild(HookBase):
    @classmethod
    def generate(cls, start=None):
        return start


def nested(classmethod):
    class Nested:
        @classmethod
        def generate(cls, start=None):
            return start

    return Nested.generate()
