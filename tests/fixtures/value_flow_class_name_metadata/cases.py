from name_state_support import NameMarker, NameSetter, install_hook, rename


class Base:
    @classmethod
    def fixed(cls, allowed=0):
        return allowed

    def __new__(cls, **kwargs):
        cls.touch()
        return cls.fixed(**kwargs)


class Fresh(Base):
    @classmethod
    def touch(cls):
        name = '_cache_' + cls.__name__
        setattr(cls, name, {})
        return getattr(cls, name)


class Inherited(Fresh):
    pass


class Alias(Fresh):
    @classmethod
    def touch(cls):
        alias = cls
        name = '_cache_' + alias.__name__
        setattr(alias, name, {})
        return getattr(alias, name)


class Lookalike(Fresh):
    __name__ = 'fixed'


class Ordinary(Fresh):
    pass


def touch_other(receiver):
    name = '_cache_' + receiver.__name__
    setattr(receiver, name, {})
    return getattr(receiver, name)


def ordinary(**kwargs):
    touch_other(Ordinary)
    return Ordinary.fixed(**kwargs)


class Conditional(Fresh):
    @classmethod
    def touch(cls):
        name = '_cache_' + cls.__name__
        if not hasattr(cls, name):
            setattr(cls, name, {})
        return getattr(cls, name)


class DeclaredRename(Fresh):
    @classmethod
    def rename(cls):
        cls.__name__ = NameMarker('renamed')


class DirectRename(Fresh):
    pass


DirectRename.__name__ = NameMarker('renamed')


class DescriptorCreation(Fresh):
    marker = NameSetter()


class GlobalEscape(Fresh):
    pass


rename(GlobalEscape)


class DefaultEscape(Fresh):
    pass


def unused(value=rename(DefaultEscape)):
    pass


class MethodEscape(Fresh):
    @classmethod
    def rename(cls):
        rename(cls)


MethodEscape.rename()


class DynamicWriter(Fresh):
    @classmethod
    def replace(cls, name, value):
        setattr(cls, name, value)


class ReflectiveWriter(Fresh):
    @classmethod
    def replace(cls, value):
        setter = setattr
        setter(cls, '__name__', value)


class HookBase(Fresh):
    def unused(self, value=install_hook()):
        pass


class HookChild(HookBase):
    pass


class VarargAnnotation(Fresh):
    def unused(self, *args: NameSetter(), **kwargs: NameSetter()):
        pass


class CustomMeta(type):
    @property
    def __name__(cls):
        return NameMarker('renamed')


class Customized(Fresh, metaclass=CustomMeta):
    pass


def customized(**kwargs):
    return Customized(**kwargs)
