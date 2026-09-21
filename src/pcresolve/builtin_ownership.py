## @package pcresolve.builtin_ownership
#  Proven Python builtin callable and receiver-shape rules for ownership.

import builtins

from .sources import PythonShape

## Python 2 builtins not present in Python 3's builtins module.
_PY2_BUILTINS = frozenset({
    "apply", "basestring", "buffer", "cmp", "coerce", "execfile",
    "file", "intern", "long", "raw_input", "reduce", "reload",
    "StandardError", "unichr", "unicode", "xrange",
})

## 1.0.5 P1: builtin container/type method names whose receiver is a
#  Python-provided object even when the receiver variable is local.
#  When a call like x.append(...) has a receiver tracing to "local"
#  and the method name is in this set, the callable owner is python.
## 1.0.5 P1: builtin container/type methods keyed by container kind.
#  The container kind (list/dict/set/tuple/str) provides context so
#  that method classification is safe from local-class name collisions.
_BUILTIN_CONTAINER_METHODS = {
    "list": frozenset([
        "append", "extend", "insert", "remove", "pop", "clear",
        "index", "count", "sort", "reverse", "copy", "__len__",
    ]),
    "dict": frozenset([
        "get", "keys", "values", "items", "update", "pop",
        "popitem", "clear", "copy", "__len__",
    ]),
    "set": frozenset([
        "add", "remove", "discard", "pop", "clear", "copy",
        "update", "difference", "intersection", "union",
        "symmetric_difference", "issubset", "issuperset", "__len__",
    ]),
    "tuple": frozenset(["count", "index", "__len__"]),
    "str": frozenset([
        "strip", "rstrip", "lstrip", "split", "rsplit", "join",
        "replace", "find", "rfind", "rindex", "startswith",
        "endswith", "upper", "lower", "title", "capitalize",
        "swapcase", "center", "ljust", "rjust", "encode", "zfill",
        "format", "format_map",
        "isalnum", "isalpha", "isascii", "isdecimal", "isdigit",
        "isidentifier", "islower", "isnumeric", "isprintable",
        "isspace", "istitle", "isupper", "__len__",
    ]),
}


## Check if a name is a Python builtin (including Python 2 builtins).
def _is_builtin(name):
    return isinstance(name, str) and (hasattr(builtins, name) or name in _PY2_BUILTINS)


## Return the runtime type corresponding to a proven PythonShape kind.
#  @param kind Concrete builtin type or container kind.
#  @return Builtin type object, or None for an unsupported shape.
def _builtin_shape_type(kind):
    if kind == "NoneType":
        return type(None)
    value = getattr(builtins, kind, None)
    return value if isinstance(value, type) else None


## Check whether a proven PythonShape exposes a callable attribute.
#  This consults the Python builtin type itself instead of maintaining a
#  method-name allowlist. Unknown receivers never reach this helper.
#  @param kind Concrete builtin type or container kind.
#  @param method Attribute name being called.
#  @return True when the builtin type defines a callable attribute.
def _has_builtin_shape_method(kind, method):
    shape_type = _builtin_shape_type(kind)
    return shape_type is not None and callable(getattr(shape_type, method, None))


## Return an established builtin method's result shape.
#  @param receiver Independently proven PythonShape, not an owner name.
#  @param method Called attribute name.
#  @return PythonShape or None without a result protocol.
def _builtin_method_return_shape(receiver, method):
    if not isinstance(receiver, PythonShape):
        return None
    if receiver.kind == "str":
        if method in ("split", "rsplit", "splitlines"):
            return PythonShape("list", "str")
        if method in (
                "strip", "rstrip", "lstrip", "replace", "upper", "lower",
                "title", "capitalize", "swapcase", "center", "ljust",
                "rjust", "zfill", "format", "format_map", "join"):
            return PythonShape("str")
    if method == "copy" and receiver.kind in ("list", "dict", "set"):
        return receiver
    return None
