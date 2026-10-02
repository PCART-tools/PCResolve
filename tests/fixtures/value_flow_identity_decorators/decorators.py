## @package value_flow_identity_decorators.decorators


## Publish metadata while returning the same callable object.
#  @param original Callable whose identity is preserved.
#  @return The original callable.
def advertise(original):
    if isinstance(original, object):
        namespace = metadata_namespace(original)
        name = metadata_name(original)
    else:
        raise TypeError("a callable is required")
    if "__all__" not in namespace:
        namespace["__all__"] = [name]
    else:
        namespace["__all__"].append(name)
    return original


## @return The unchanged callable.
def pure_identity(original):
    return original


## @return A source-defined callable replacing the input.
def replace(original):
    def replacement(value):
        return None
    return replacement


## @return A wrapper whose capture requires separate reasoning.
def wrap(original):
    def wrapper(value):
        return original(value)
    return wrapper


## @return An unknown value after rebinding the original formal.
def rebind(original):
    original = unknown_callable
    return original


## @return No proven callable after deleting the original formal.
def delete(original):
    del original
    return original


## @return The original callable or a replacement.
def conditional_replace(original):
    if replace_enabled:
        return unknown_callable
    return original


## @return The original callable only on one path.
def fallthrough(original):
    if publish_enabled:
        return original


## @return A coroutine instead of the input callable.
async def async_identity(original):
    return original


## @return A generator instead of the input callable.
def generator_identity(original):
    yield None
    return original


## @return The same object after changing its code, without source transparency.
def mutate_code(original):
    original.__code__ = unknown_callable.__code__
    return original


## @return The same object after changing its code through an alias.
def mutate_alias_code(original):
    alias = original
    alias.__code__ = unknown_callable.__code__
    return original


## @return A coroutine containing a replacement, rather than the replacement.
async def async_replace(original):
    def replacement(value):
        return None
    return replacement
