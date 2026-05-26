## @package pcresolve.sources
#  Typed source IR and compatibility helpers.
#
#  Provides frozen dataclasses to replace bare legacy tuples
#  ("container_item", ...) etc., plus normalise/display/legacy adapters.

from dataclasses import dataclass
from typing import Union


## Source for a simple name or module path.
@dataclass(frozen=True)
class NameSource:
    ## Name or dotted module path.
    name: str


## Source for container item access, such as mapping["key"].
@dataclass(frozen=True)
class ContainerItem:
    ## Container symbol (name or nested source).
    container: "SourceLike"
    ## Item index or key (int, str, etc.).
    index: object


## Source for iteration over a container.
@dataclass(frozen=True)
class ContainerIter:
    ## Container symbol (name or nested source).
    container: "SourceLike"


## Source for a method resolved through an instance or class.
@dataclass(frozen=True)
class InstanceMethod:
    ## Receiver symbol or source.
    receiver: "SourceLike"
    ## Method name.
    method: str


## Source for the result of calling a function.
@dataclass(frozen=True)
class CallResult:
    ## Callee symbol or source.
    callee: "SourceLike"
    ## Optional display name (e.g. "np.array") for provenance chains.
    display_name: str = ""


## Unknown source that preserves display context.
@dataclass(frozen=True)
class UnknownSource:
    ## Human-readable representation.
    display: str = ""


## Union of all Source IR types and plain strings.
SourceLike = Union[str, NameSource, ContainerItem, ContainerIter, InstanceMethod, CallResult, UnknownSource]


## Ordered set of possible sources (for multi-value bindings).
@dataclass(frozen=True)
class SourceSet:
    ## Tuple of possible sources.
    sources: tuple


## Build a SourceSet from a sequence of source values, deduplicating by display.
#
#  @param values Iterable of source values.
#  @return SourceSet with deduplicated, stable-ordered sources.
def make_source_set(values):
    items = []
    for value in values:
        norm = normalize_source(value)
        if isinstance(norm, SourceSet):
            items.extend(norm.sources)
        elif norm is not None:
            items.append(norm)
    seen = set()
    deduped = []
    for item in items:
        key = source_display(item)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return SourceSet(tuple(deduped))


## Check whether a value is a structured source (dataclass or legacy tuple).
#
#  @param value Source value to test.
#  @return True if the value is a structured (non-string) source.
def is_structured_source(value):
    if isinstance(value, tuple) and len(value) == 3 and isinstance(value[0], str):
        return True
    if isinstance(value, (ContainerItem, ContainerIter, InstanceMethod, CallResult, UnknownSource, NameSource)):
        return True
    return False


## Normalize legacy tuple/string source values into Source IR where possible.
#
#  @param value Legacy source value or Source IR object.
#  @return Normalized source value.
def normalize_source(value):
    if isinstance(value, tuple) and len(value) == 3:
        kind, a, b = value
        if kind == "container_item":
            return ContainerItem(a, b)
        if kind == "container_iter":
            return ContainerIter(a)
        if kind == "instance_method":
            return InstanceMethod(a, b)
        if kind == "call_result":
            return CallResult(a)
    return value


## Convert Source IR back to legacy tuple form where needed.
#
#  @param value Source value.
#  @return Legacy-compatible source value.
def source_to_legacy(value):
    if isinstance(value, ContainerItem):
        return ("container_item", value.container, value.index)
    if isinstance(value, ContainerIter):
        return ("container_iter", value.container, "*")
    if isinstance(value, InstanceMethod):
        return ("instance_method", value.receiver, value.method)
    if isinstance(value, CallResult):
        return ("call_result", value.callee, None)
    return value


## Return a stable human-readable representation of a source value.
#
#  Recursively formats nested structures without leaking dataclass reprs.
#  @param value Source value.
#  @return Display string.
def source_display(value):
    value = normalize_source(value)
    if isinstance(value, ContainerItem):
        return "%s[%s]" % (source_display(value.container), value.index)
    if isinstance(value, ContainerIter):
        return "%s[*]" % source_display(value.container)
    if isinstance(value, InstanceMethod):
        return "%s.%s" % (source_display(value.receiver), value.method)
    if isinstance(value, CallResult):
        if value.display_name:
            return "%s()" % value.display_name
        return "%s()" % source_display(value.callee)
    if isinstance(value, NameSource):
        return value.name
    if isinstance(value, UnknownSource):
        return value.display
    return str(value)
