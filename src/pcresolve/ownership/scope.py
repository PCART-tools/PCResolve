## @package pcresolve.ownership.scope
#  Lexical scope and binding model.
#  词法作用域与绑定模型。

from dataclasses import dataclass, field
from typing import Optional


SCOPE_MODULE = "module"
SCOPE_FUNCTION = "function"
SCOPE_CLASS = "class"
SCOPE_COMPREHENSION = "comprehension"


## A source binding for a symbol in one lexical scope.
## 单个词法作用域中符号的来源绑定。
@dataclass
class Binding:
    ## Symbol name.
    name: str
    ## Source or source set.
    source: object
    ## Scope kind where the binding was created.
    scope_kind: str = ""
    ## Source line.
    lineno: int = 0
    ## Source column.
    col_offset: int = 0
    ## Monotonic assignment index within the file or scope.
    assignment_index: int = 0
    ## Binding version for future flow-sensitive analysis.
    version: int = 0
    ## Concrete Python container kind carried by this binding, if known.
    container_kind: str = ""
    ## Concrete kind produced by subscripting this container, if known.
    container_item_kind: str = ""
    ## Field shapes carried by a known container element, if any.
    container_item_fields: dict = field(default_factory=dict)
    ## Qualified return_sources key when this binding is a local callable.
    callable_key: str = ""
    ## Binding role such as parameter, variable, import, or attribute.
    binding_kind: str = ""
    ## Private literal-mapping value for local callback identity only.
    mapping_value: object = None


## A lexical scope with parent lookup.
## 支持沿父作用域查找的词法作用域。
@dataclass
class Scope:
    ## Scope kind.
    kind: str
    ## Human-readable scope name.
    name: str = ""
    ## Parent scope.
    parent: object = None
    ## Bindings in this scope.
    bindings: dict = field(default_factory=dict)

    ## Bind a name in the current scope.
    ## 在当前作用域绑定名称。
    #
    #  @param name Symbol name.
    #  @param source Source value.
    #  @param lineno Source line.
    #  @param col_offset Source column.
    #  @param assignment_index Monotonic assignment counter.
    #  @param container_kind Concrete receiver container kind, if known.
    #  @param container_item_kind Concrete subscript result kind, if known.
    #  @param callable_key Qualified return_sources key for local callables.
    #  @param binding_kind Binding role used for flow-sensitive checks.
    #  @param container_item_fields Known field shapes of a container element.
    #  @return None
    def bind(self, name, source, lineno=0, col_offset=0, assignment_index=0,
             container_kind="", container_item_kind="", callable_key="",
             binding_kind="", container_item_fields=None):
        old = self.bindings.get(name)
        version = old.version + 1 if old is not None else 1
        self.bindings[name] = Binding(
            name, source, self.kind, lineno, col_offset,
            assignment_index, version, container_kind,
            container_item_kind,
            dict(container_item_fields or {}), callable_key, binding_kind,
        )

    ## Look up a name through lexical parents.
    ## 沿词法父作用域查找名称。
    #
    #  @param name Symbol name.
    #  @param skip_parent_classes If True, skip parent class-scope
    #         bindings (Python does not resolve bare names through
    #         enclosing class namespace — only self/attr).  The
    #         starting scope's own bindings are always searched.
    #  @return Binding object or None.
    def lookup(self, name: str,
               skip_parent_classes: bool = False) -> Optional[Binding]:
        scope = self
        is_origin = True
        while scope is not None:
            # The starting class scope remains visible even when parent classes are skipped.
            # 即使跳过父类作用域，仍搜索作为起点的类作用域。
            should_search = (
                is_origin
                or not (
                    skip_parent_classes
                    and scope.kind == SCOPE_CLASS
                )
            )
            if should_search and name in scope.bindings:
                return scope.bindings[name]
            is_origin = False
            scope = scope.parent
        return None

    ## Return a shallow copy of current bindings (for branch snapshots).
    ## 返回当前绑定的浅拷贝，供分支快照使用。
    #
    #  @return Dict copy of bindings.
    def snapshot(self):
        return dict(self.bindings)

    ## Restore bindings from a snapshot.
    ## 从快照恢复绑定。
    #
    #  @param state Dict of bindings or Scope whose bindings to copy.
    #  @return None
    def restore(self, state):
        if isinstance(state, Scope):
            self.bindings = dict(state.bindings)
        else:
            self.bindings = dict(state)


## Merge two branch snapshots with a base.
## 结合基线合并两个分支快照。
#
#  - Both unchanged from base: keep base.
#  - One branch changed, other unchanged: SourceSet([changed, base])
#    (or just changed if base had no binding for that name).
#  - Both changed to same value: keep single value.
#  - Both changed to different values: SourceSet([left, right]).
#
#  @param base Base snapshot dict.
#  @param left Left branch snapshot dict.
#  @param right Right branch snapshot dict.
#  @return Merged bindings dict.
def merge_snapshots(base, left, right):
    merged = {}
    all_names = set(base.keys()) | set(left.keys()) | set(right.keys())
    for name in all_names:
        bv = base.get(name)
        lv = left.get(name)
        rv = right.get(name)
        if lv == rv:
            merged[name] = lv if lv is not None else bv
        elif bv is not None and lv == bv and rv is not None:
            # Only right changed: SourceSet([base, right])
            merged[name] = _merge_two(bv, rv)
        elif bv is not None and rv == bv and lv is not None:
            # Only left changed: SourceSet([base, left])
            merged[name] = _merge_two(bv, lv)
        elif lv is None and rv is not None and bv is not None:
            # Right added new binding while left deleted: keep base
            merged[name] = _merge_two(bv, rv)
        elif rv is None and lv is not None and bv is not None:
            # Left added new binding while right deleted: keep base
            merged[name] = _merge_two(bv, lv)
        elif lv is not None and rv is not None:
            merged[name] = _merge_two(lv, rv)
        elif lv is not None:
            merged[name] = lv
        else:
            merged[name] = rv
    return merged


## Merge two branch sources while retaining distinct located call results.
## 合并两个分支来源，并保留位置不同的调用结果。
#
#  @param left_binding Left binding or source.
#  @param right_binding Right binding or source.
#  @return SourceSet of deduplicated alternatives.
def _merge_two(left_binding, right_binding):
    from pcresolve.ownership.sources import source_display, CallResult, SourceSet as SS
    ## Include call-site location when distinguishing call results.
    ## 区分调用结果时将调用点位置纳入键。
    #
    #  @param src Source alternative.
    #  @return Display-based merge key with optional call location.
    def _merge_key(src):
        key = source_display(src)
        if isinstance(src, CallResult) and src.call_lineno:
            key = "%s@L%dC%d" % (key, src.call_lineno, src.call_col_offset)
        return key
    left_src = left_binding.source if isinstance(left_binding, Binding) else left_binding
    right_src = right_binding.source if isinstance(right_binding, Binding) else right_binding
    items = []
    seen = set()
    # Flatten source sets while preserving the first occurrence of each key.
    # 展平来源集合，同时保留各键首次出现的顺序。
    for src in (left_src, right_src):
        if isinstance(src, SS):
            for s in src.sources:
                key = _merge_key(s)
                if key not in seen:
                    seen.add(key)
                    items.append(s)
        elif src is not None:
            key = _merge_key(src)
            if key not in seen:
                seen.add(key)
                items.append(src)
    return SS(tuple(items))
