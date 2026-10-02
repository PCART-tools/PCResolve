## @package value_flow_identity_decorators.targets

from api import exported_decorator as announce
from decorators import (pure_identity, replace, wrap, rebind, delete,
                        conditional_replace, fallthrough, async_identity,
                        generator_identity, mutate_code, mutate_alias_code,
                        async_replace)


## @return The supplied value through a metadata-only decorator.
@announce
def advertised(value):
    return value


## @return The supplied value through a minimal identity decorator.
@pure_identity
def pure(value):
    return value


## @return A constant installed by the replacement decorator.
@replace
def replaced(value):
    return value


## @return The wrapper's result, without proving the original is the target.
@wrap
def wrapped(value):
    return value


## @return The result of an unknown decorator.
@unknown_decorator
def unknown(value):
    return value


## @return The result of a decorator rebinding its formal.
@rebind
def rebound_formal(value):
    return value


## @return The result of a decorator deleting its formal.
@delete
def deleted_formal(value):
    return value


## @return The result of a decorator with a replacement return path.
@conditional_replace
def conditional(value):
    return value


## @return The result of a decorator with an implicit None path.
@fallthrough
def incomplete(value):
    return value


## @return A coroutine decorator's result.
@async_identity
def asynchronous(value):
    return value


## @return A generator decorator's result.
@generator_identity
def generator(value):
    return value


## @return The result after code mutation.
@mutate_code
def code_changed(value):
    return value


## @return The result after an aliased callable code mutation.
@mutate_alias_code
def alias_code_changed(value):
    return value


## @return The result of an asynchronous replacement decorator.
@async_replace
def asynchronously_replaced(value):
    return value


class Holder:
    announce = unknown_decorator

    ## @return The result of a class-local shadowing decorator.
    @announce
    def shadowed(self, value):
        return value
