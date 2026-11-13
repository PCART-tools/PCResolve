## @package pcresolve.sources
#  Typed source IR and compatibility helpers.
#
#  Provides frozen dataclasses to replace bare legacy tuples
#  ("container_item", ...) etc., plus normalise/display/legacy adapters.
#  提供类型化来源中间表示以及规范化、展示和旧格式适配工具。

from dataclasses import dataclass
from typing import Optional, Union


## Source for a simple name or module path.
## 简单名称或模块路径的来源。
@dataclass(frozen=True)
class NameSource:
    ## Name or dotted module path.
    name: str


## Source for container item access, such as mapping["key"].
## 容器元素访问的来源，例如 mapping["key"]。
@dataclass(frozen=True)
class ContainerItem:
    ## Container symbol (name or nested source).
    container: "SourceLike"
    ## Item index or key (int, str, etc.).
    index: object


## Source for iteration over a container.
## 遍历容器所得元素的来源。
@dataclass(frozen=True)
class ContainerIter:
    ## Container symbol (name or nested source).
    container: "SourceLike"


## Source for one homogeneous tuple/list element shape.
## 同形元组或列表元素的字段来源。
#
#  This is an internal call-graph fact.  It preserves the field sources of a
#  tuple appended to a local iterable, without claiming that the iterable
#  object itself owns those fields.
@dataclass(frozen=True)
class TupleSource:
    ## Ordered field sources.
    items: tuple


## Source for a method resolved through an instance or class.
## 通过实例或类解析的方法来源。
@dataclass(frozen=True)
class InstanceMethod:
    ## Receiver symbol or source.
    receiver: "SourceLike"
    ## Method name.
    method: str
    ## Qualified local function scope when the receiver is a parameter.
    #
    #  Empty for ordinary receivers. This is internal analysis metadata and
    #  is intentionally omitted from the legacy tuple adapter.
    parameter_scope: str = ""
    ## Root parameter name for dotted receivers such as stream.socket.
    parameter_name: str = ""


## Source for a value forwarded from a local function parameter.
## 从本地函数参数转发的值的来源。
@dataclass(frozen=True)
class ParameterSource:
    ## Qualified local function or method scope.
    scope: str
    ## Parameter name within that scope.
    name: str
    ## Whether the value passed through an unsupported derived operation.
    derived: bool = False
    ## Statically preserved attribute path from the root parameter.
    attributes: tuple = ()
    ## Derived operation applied to the parameter value, when known.
    #  Only operations with a statically preserved shape are recorded.
    derived_operation: str = ""


## Source for an instance field whose binding depends on runtime subclass.
## 绑定取决于运行时子类的实例字段来源。
#
#  A base-class method may read ``self.payload`` even though only a local
#  subclass assigns that field. Cross-file analysis resolves the field from
#  the concrete project call edges that reach the base method.
@dataclass(frozen=True)
class InstanceAttribute:
    ## Class that lexically contains the field read.
    class_name: str
    ## Normalized field path, for example ``self.payload``.
    attribute: str
    ## Qualified method containing the field read.
    scope: str


## Concrete Python-provided value shape preserved across local call edges.
## 跨本地调用边保留的具体 Python 值形态。
#
#  This is language-level evidence, not an import-library return contract.
#  It lets parameter method resolution distinguish, for example, a string
#  argument from an integer without inferring ownership from the method name.
@dataclass(frozen=True)
class PythonShape:
    ## Concrete builtin type or container kind.
    kind: str
    ## Concrete item kind for homogeneous containers, when known.
    item_kind: str = ""


## Source for a super().method() call, capturing enclosing class context.
## 保存外层类上下文的 super().method() 调用来源。
#
#  Generated in single-file AST visit when _class_stack is available.
#  Cross-file resolves the method owner from the class's base classes.
@dataclass(frozen=True)
class SuperMethod:
    ## Class key matching the current class_bases / class_methods index
    #  (bare class name, not qualname).
    class_key: str
    ## Full nested qualname for display and evidence (e.g. "Outer.Inner").
    class_qualname: str
    ## The method being called on super().
    method: str


## Source for the result of calling a function.
## 函数调用结果的来源。
@dataclass(frozen=True)
class CallResult:
    ## Callee symbol or source.
    callee: "SourceLike"
    ## Optional display name (e.g. "np.array") for provenance chains.
    display_name: str = ""
    ## Line number of the call site that produced this result (0 = unknown).
    call_lineno: int = 0
    ## Column offset of the call site (0 = unknown).
    call_col_offset: int = 0
    ## Module in which the call expression was analyzed.
    #  Needed when a declaration-time expression, such as a function default,
    #  has no runtime call edge but still carries an aliased source symbol.
    source_module: str = ""
    ## Where the return-object gets its ownership from.
    #
    #  - None (default): unresolved — continue existing return_sources /
    #    call-graph path.
    #  - UnknownSource: statically unresolvable (e.g. eval, dynamic __import__).
    #  - "python": result object is a Python-provided type (e.g. open, list, str).
    #  - DerivedResult: structured semantics carrying operands for cross-file
    #    resolution (e.g. element-derived, attribute-derived).
    result_source: "Optional[SourceLike]" = None


## Structured result-object source carrying operands for cross-file resolution.
## 携带操作数供跨文件解析的结构化结果对象来源。
#
#  Used as CallResult.result_source for builtin calls whose return type
#  depends on their arguments (e.g. next, getattr, type, __import__).
@dataclass(frozen=True)
class DerivedResult:
    ## Semantic kind: "element", "iterator", "attribute", "callback",
    #  "constant_import", "protocol", "python", "expression".
    kind: str
    ## SourceLike operands needed to resolve the result owner.
    sources: tuple
    ## Attribute name for "attribute" kind (e.g. getattr).
    attribute: str = ""


## Unknown source that preserves display context.
## 保留展示上下文的未知来源。
@dataclass(frozen=True)
class UnknownSource:
    ## Human-readable representation.
    display: str = ""


## Ordered set of possible sources (for multi-value bindings).
## 多值绑定可能来源的有序集合。
@dataclass(frozen=True)
class SourceSet:
    ## Tuple of possible sources.
    sources: tuple
    ## Provenance origin hint: "dict_lookup", "return", "builtin_element",
    #  or "" (unspecified).
    origin: str = ""


## Union of all Source IR types and plain strings.
SourceLike = Union[str, NameSource, ContainerItem, ContainerIter, InstanceMethod,
                   TupleSource, ParameterSource, InstanceAttribute, PythonShape,
                   SuperMethod, CallResult, DerivedResult, SourceSet, UnknownSource]
## Build a SourceSet from an iterable of source values, deduplicating by display.
## 根据来源值序列构造 SourceSet，并按展示形式去重。
#
#  @param values Iterable of source values.
#  @param origin Optional provenance origin hint; mixed hints become mixed.
#  @return SourceSet with deduplicated, stable-ordered sources.
def make_source_set(values, origin=""):
    items = []
    for value in values:
        norm = normalize_source(value)
        if isinstance(norm, SourceSet):
            items.extend(norm.sources)
            if not origin and norm.origin:
                origin = norm.origin
            elif origin and norm.origin and origin != norm.origin:
                origin = "mixed"
        elif norm is not None:
            items.append(norm)
    # Preserve first-seen order while retaining the established display-based identity.
    # 沿用基于展示形式的身份规则，并保留首次出现的顺序。
    seen = set()
    deduped = []
    for item in items:
        key = source_display(item)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return SourceSet(tuple(deduped), origin=origin)


## Check whether a value is a structured source (dataclass or legacy tuple).
## 判断值是否为结构化来源（数据类或旧格式元组）。
#
#  @param value Source value to test.
#  @return True if the value is a structured (non-string) source.
def is_structured_source(value):
    if isinstance(value, tuple) and len(value) == 3 and isinstance(value[0], str):
        return True
    if isinstance(value, (ContainerItem, ContainerIter, TupleSource, InstanceMethod,
                          ParameterSource, InstanceAttribute, PythonShape,
                          SuperMethod, CallResult, DerivedResult, SourceSet,
                          UnknownSource, NameSource)):
        return True
    return False


## Normalize legacy tuple/string source values into Source IR where possible.
## 在可转换时将旧格式来源值规范化为来源中间表示。
#
#  @param value Legacy source value or Source IR object.
#  @return Normalized source value.
def normalize_source(value):
    if isinstance(value, tuple) and len(value) == 3:
        kind, a, b = value
        if kind == "container_item":
            return ContainerItem(normalize_source(a), b)
        if kind == "container_iter":
            return ContainerIter(normalize_source(a))
        if kind == "tuple_source":
            values = a if isinstance(a, (tuple, list)) else ()
            return TupleSource(tuple(normalize_source(s) for s in values))
        if kind == "instance_method":
            return InstanceMethod(normalize_source(a), b)
        if kind == "parameter_source":
            if isinstance(a, tuple) and len(a) >= 2:
                attributes = tuple(a[2]) if len(a) >= 3 else ()
                operation = a[3] if len(a) >= 4 else ""
                return ParameterSource(
                    a[0], b, bool(a[1]), attributes=attributes,
                    derived_operation=operation)
            return ParameterSource(a, b)
        if kind == "instance_attribute":
            if isinstance(a, tuple) and len(a) == 2:
                return InstanceAttribute(a[0], b, a[1])
            return InstanceAttribute(a, b, "")
        if kind == "python_shape":
            return PythonShape(a, b or "")
        if kind == "call_result":
            rs = normalize_source(b) if b is not None else None
            return CallResult(normalize_source(a), result_source=rs)
        if kind == "super_method":
            # Legacy tuple: ("super_method", class_key, method)
            # Extended: ("super_method", (class_key, class_qualname), method)
            if isinstance(a, tuple) and len(a) == 2:
                return SuperMethod(normalize_source(a[0]), normalize_source(a[1]), b)
            return SuperMethod(normalize_source(a), normalize_source(a), b)
        if kind == "derived_result":
            # ("derived_result", (kind, serialized_sources), attribute)
            if isinstance(a, tuple) and len(a) == 2:
                return DerivedResult(a[0], tuple(normalize_source(s) for s in a[1]), b or "")
            return DerivedResult(normalize_source(a), (), b or "")
        if kind == "source_set":
            values = a if isinstance(a, (tuple, list)) else ()
            return SourceSet(tuple(normalize_source(s) for s in values), b or "")
        if kind == "name_source":
            return NameSource(a)
        if kind == "unknown_source":
            return UnknownSource(a or "")
    return value


## Convert Source IR back to legacy tuple form where needed.
## 在需要时将来源中间表示转换回旧格式元组。
#
#  @param value Source value.
#  @return Legacy-compatible source value.
def source_to_legacy(value):
    if isinstance(value, ContainerItem):
        return ("container_item", source_to_legacy(value.container), value.index)
    if isinstance(value, ContainerIter):
        return ("container_iter", source_to_legacy(value.container), "*")
    if isinstance(value, TupleSource):
        return ("tuple_source",
                tuple(source_to_legacy(s) for s in value.items), None)
    if isinstance(value, InstanceMethod):
        return ("instance_method", source_to_legacy(value.receiver), value.method)
    if isinstance(value, ParameterSource):
        metadata = (value.scope, value.derived, tuple(value.attributes))
        if value.derived_operation:
            metadata += (value.derived_operation,)
        return (
            "parameter_source",
            metadata,
            value.name,
        )
    if isinstance(value, InstanceAttribute):
        return (
            "instance_attribute",
            (value.class_name, value.scope),
            value.attribute,
        )
    if isinstance(value, PythonShape):
        return ("python_shape", value.kind, value.item_kind)
    if isinstance(value, CallResult):
        rs = getattr(value, 'result_source', None)
        return ("call_result", source_to_legacy(value.callee),
                source_to_legacy(rs) if rs is not None else None)
    if isinstance(value, SuperMethod):
        return ("super_method", (value.class_key, value.class_qualname), value.method)
    if isinstance(value, DerivedResult):
        return ("derived_result",
                (value.kind, tuple(source_to_legacy(s) for s in value.sources)),
                value.attribute)
    if isinstance(value, SourceSet):
        return ("source_set",
                tuple(source_to_legacy(s) for s in value.sources),
                value.origin)
    if isinstance(value, NameSource):
        return ("name_source", value.name, None)
    if isinstance(value, UnknownSource):
        return ("unknown_source", value.display, None)
    return value


## Return a stable human-readable representation of a source value.
## 返回来源值稳定且可读的展示形式。
#
#  Recursively formats nested structures without leaking dataclass reprs.
#
#  @param value Source value.
#  @return Display string.
def source_display(value):
    value = normalize_source(value)
    if isinstance(value, ContainerItem):
        return "%s[%s]" % (source_display(value.container), value.index)
    if isinstance(value, ContainerIter):
        return "%s[*]" % source_display(value.container)
    if isinstance(value, TupleSource):
        return "(" + ", ".join(source_display(s) for s in value.items) + ")"
    if isinstance(value, InstanceMethod):
        return "%s.%s" % (source_display(value.receiver), value.method)
    if isinstance(value, ParameterSource):
        path = "".join(".%s" % part for part in value.attributes)
        suffix = "*" if value.derived else ""
        return "%s:%s%s%s" % (
            value.scope, value.name, path, suffix)
    if isinstance(value, InstanceAttribute):
        return "%s:%s" % (value.class_name, value.attribute)
    if isinstance(value, PythonShape):
        if value.item_kind:
            return "python:%s[%s]" % (value.kind, value.item_kind)
        return "python:%s" % value.kind
    if isinstance(value, CallResult):
        if value.display_name:
            return "%s()" % value.display_name
        return "%s()" % source_display(value.callee)
    if isinstance(value, SuperMethod):
        return "super().%s" % value.method
    if isinstance(value, DerivedResult):
        if value.kind == "attribute" and value.attribute:
            return "DerivedResult(%s, attr=%s)" % (value.kind, value.attribute)
        return "DerivedResult(%s)" % value.kind
    if isinstance(value, SourceSet):
        return "[" + ", ".join(source_display(s) for s in value.sources) + "]"
    if isinstance(value, NameSource):
        return value.name
    if isinstance(value, UnknownSource):
        return value.display
    return str(value)
