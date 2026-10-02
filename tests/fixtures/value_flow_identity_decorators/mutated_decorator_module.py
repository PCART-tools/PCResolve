## @package value_flow_identity_decorators.mutated_decorator_module

import decorators as decoration_module

decoration_module.pure_identity = unknown_decorator


## @return The result of a decorator overwritten through a module alias.
@decoration_module.pure_identity
def mutated(value):
    return value
