## @package value_flow_identity_decorators.consumer

import targets
from rebound_decorator import rebound
from mutated_decorator_module import mutated


## @return The identity-decorated source function's result.
def advertised(value):
    return targets.advertised(value)


## @return The minimally decorated source function's result.
def pure(value):
    return targets.pure(value)


## @return The replacement's result.
def replaced(value):
    return targets.replaced(value)


## @return The wrapper's result.
def wrapped(value):
    return targets.wrapped(value)


## @return The unknown decorator's result.
def unknown(value):
    return targets.unknown(value)


## @return The formal-rebinding decorator's result.
def rebound_formal(value):
    return targets.rebound_formal(value)


## @return The formal-deleting decorator's result.
def deleted_formal(value):
    return targets.deleted_formal(value)


## @return The conditional decorator's result.
def conditional(value):
    return targets.conditional(value)


## @return The fallthrough decorator's result.
def incomplete(value):
    return targets.incomplete(value)


## @return The asynchronous decorator's result.
def asynchronous(value):
    return targets.asynchronous(value)


## @return The generator decorator's result.
def generator(value):
    return targets.generator(value)


## @return The changed callable's result.
def code_changed(value):
    return targets.code_changed(value)


## @return The decorator-symbol-rebinding result.
def rebound_symbol(value):
    return rebound(value)


## @return The class-shadowed decorator's result.
def class_shadow(value):
    return targets.Holder.shadowed(None, value)


## @return The changed callable's result after alias-based mutation.
def alias_code_changed(value):
    return targets.alias_code_changed(value)


## @return The asynchronous replacement decorator's result.
def asynchronously_replaced(value):
    return targets.asynchronously_replaced(value)


## @return The module-attribute-overwritten decorator's result.
def module_attribute_changed(value):
    return mutated(value)
