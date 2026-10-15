from literal_state_backend import Imported as Alias
import literal_state_backend as backend


class Entry:
    @classmethod
    def fixed(cls, token=None, allowed=0):
        return allowed


class Static:
    @staticmethod
    def fixed(token=None, allowed=0):
        return allowed


class Derived(Entry):
    pass


def after(**kwargs):
    external(Entry)
    return Entry.fixed(**kwargs)


def after_static(**kwargs):
    external(Static)
    return Static.fixed(**kwargs)


def after_alias(**kwargs):
    external(Alias)
    return Alias.fixed(**kwargs)


def after_module(**kwargs):
    external(backend.Imported)
    return backend.Imported.fixed(**kwargs)


def after_base(**kwargs):
    external(Entry)
    return Derived.fixed(**kwargs)


def selected(**kwargs):
    return Entry.fixed(token=external(Entry), **kwargs)


def selected_static(**kwargs):
    return Static.fixed(token=external(Static), **kwargs)


def direct(**kwargs):
    return Entry.fixed(**kwargs)


def fixed(allowed=0):
    return allowed


def ordinary_callable(**kwargs):
    target = fixed
    external(Entry)
    return target(**kwargs)
