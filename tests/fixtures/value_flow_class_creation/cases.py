import inspect
from creation_support import ReadDescriptor


def fixed(allowed=0):
    return allowed


def replacement(cls, **kwargs):
    return kwargs


class Base:
    def __new__(cls, **kwargs):
        return fixed(**kwargs)


class Literal(Base):
    marker = {'counter': 0}

    @classmethod
    def label(cls, value: str = 'literal') -> str:
        return value

    @staticmethod
    def unused(*args: str, **kwargs: str):
        pass


class Derived(Literal):
    pass


class DescriptorSafe(Base):
    token = ReadDescriptor()


def descriptor_safe(**kwargs):
    return DescriptorSafe(**kwargs)


def install_hook():
    namespace = inspect.currentframe().f_back.f_locals

    def initialize(child):
        child.__new__ = staticmethod(replacement)

    namespace['__init_subclass__'] = classmethod(initialize)


class HiddenBase(Base):
    def unused(self, value=install_hook()):
        pass


class Hidden(HiddenBase):
    pass


class ReplacesEntry:
    def __set_name__(self, owner, name):
        owner.__new__ = staticmethod(replacement)


class DescriptorEntry(Base):
    marker = ReplacesEntry()


def install_entry():
    namespace = inspect.currentframe().f_back.f_locals
    namespace['__new__'] = staticmethod(replacement)


class AnnotationEntry(Base):
    def unused(self, *args: install_entry()):
        pass


class Initializer:
    def __init__(self):
        namespace = inspect.currentframe().f_back.f_locals
        namespace['__new__'] = staticmethod(replacement)


class FactoryEntry(Base):
    token = Initializer()


class MutableValue:
    pass


def replace_owner(self, owner, name):
    owner.__new__ = staticmethod(replacement)


MutableValue.__set_name__ = replace_owner


class WrittenDescriptor(Base):
    token = MutableValue()


class ShadowedFactory(Base):
    def ReadDescriptor():
        namespace = inspect.currentframe().f_back.f_locals
        namespace['__new__'] = staticmethod(replacement)
        return {}

    token = ReadDescriptor()


def hidden(**kwargs):
    return Hidden(**kwargs)


def descriptor(**kwargs):
    return DescriptorEntry(**kwargs)


def annotation(**kwargs):
    return AnnotationEntry(**kwargs)


def factory(**kwargs):
    return FactoryEntry(**kwargs)


def written(**kwargs):
    return WrittenDescriptor(**kwargs)


def shadowed(**kwargs):
    return ShadowedFactory(**kwargs)
