## @package value_flow_identity_decorators.rebound_decorator

from decorators import pure_identity as decoration

decoration = unknown_decorator


## @return The result of a rebound decorator symbol.
@decoration
def rebound(value):
    return value
