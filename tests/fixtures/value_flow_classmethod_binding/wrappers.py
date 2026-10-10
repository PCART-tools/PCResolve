from targets import (Backend, Derived, Override, Patched, Reflected, Escaped,
                     CustomMeta, Decorated, DescriptorChild, Shadowed,
                     Conditional, Alias, factory, relay)
from targets import Indirect, GlobalWrite, Deleted, HookChild, CodeWrite, BuiltinAliasWrite
from targets import BranchWrite
from targets import Backend as ImportedAlias
import targets as api


def direct(**kwargs):
    return Backend.generate(**kwargs)


def imported_alias(**kwargs):
    return ImportedAlias.generate(**kwargs)


def module_alias(**kwargs):
    return api.Backend.generate(**kwargs)


def local_alias(**kwargs):
    alias = Backend
    return alias.generate(**kwargs)


def exported_alias(**kwargs):
    return Alias.generate(**kwargs)


def inherited(**kwargs):
    return Derived.generate(**kwargs)


def overridden(**kwargs):
    return Override.generate(**kwargs)


def rebound(**kwargs):
    Backend = unknown_class
    return Backend.generate(**kwargs)


def patched(**kwargs):
    alias = Patched
    alias.generate = unknown_callable
    return Patched.generate(**kwargs)


def reflected(**kwargs):
    setattr(Reflected, 'generate', unknown_callable)
    return Reflected.generate(**kwargs)


def escaped(**kwargs):
    unknown_effect(Escaped)
    return Escaped.generate(**kwargs)


def unknown(receiver, **kwargs):
    return receiver.generate(**kwargs)


def mixed(flag, **kwargs):
    receiver = Backend if flag else Override
    return receiver.generate(**kwargs)


def returned(**kwargs):
    receiver = factory()
    return receiver.generate(**kwargs)


def unknown_factory(**kwargs):
    receiver = unknown_factory_call()
    return receiver.generate(**kwargs)


def custom_meta(**kwargs):
    return CustomMeta.generate(**kwargs)


def decorated(**kwargs):
    return Decorated.generate(**kwargs)


def descriptor(**kwargs):
    return DescriptorChild.generate(**kwargs)


def shadowed(**kwargs):
    return Shadowed.generate(**kwargs)


def conditional(**kwargs):
    return Conditional.generate(**kwargs)


def contexts(**kwargs):
    return relay(**kwargs), direct(**kwargs)


def mutate(receiver):
    setattr(receiver, 'generate', unknown_callable)


def indirect(**kwargs):
    mutate(Indirect)
    return Indirect.generate(**kwargs)


def global_write(**kwargs):
    return GlobalWrite.generate(**kwargs)


def deleted(**kwargs):
    delattr(Deleted, 'generate')
    return Deleted.generate(**kwargs)


def hook(**kwargs):
    return HookChild.generate(**kwargs)


def code_write(**kwargs):
    CodeWrite.generate.__func__.__code__ = unknown_code
    return CodeWrite.generate(**kwargs)


def global_code_write(**kwargs):
    return CodeWrite.generate(**kwargs)


def builtin_alias_write(**kwargs):
    return BuiltinAliasWrite.generate(**kwargs)


def branch_write(**kwargs):
    return BranchWrite.generate(**kwargs)


def selected(flag, mapping):
    if flag:
        receiver = Backend
    else:
        receiver = factory()
    return receiver.generate(**mapping)


def merged_contexts(**kwargs):
    return selected(True, kwargs), selected(False, kwargs)
