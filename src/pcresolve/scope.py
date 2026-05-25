## @package pcresolve.scope
#  Lexical scope and binding model.

from dataclasses import dataclass, field


SCOPE_MODULE = "module"
SCOPE_FUNCTION = "function"
SCOPE_CLASS = "class"
SCOPE_COMPREHENSION = "comprehension"


## A source binding for a symbol in one lexical scope.
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


## A lexical scope with parent lookup.
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
    #  @param name Symbol name.
    #  @param source Source value.
    #  @param lineno Source line.
    #  @param col_offset Source column.
    #  @param assignment_index Monotonic assignment counter.
    def bind(self, name, source, lineno=0, col_offset=0, assignment_index=0):
        old = self.bindings.get(name)
        version = old.version + 1 if old is not None else 1
        self.bindings[name] = Binding(
            name, source, self.kind, lineno, col_offset,
            assignment_index, version,
        )

    ## Look up a name through lexical parents.
    #  @param name Symbol name.
    #  @return Binding object or None.
    def lookup(self, name):
        if name in self.bindings:
            return self.bindings[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    ## Return a shallow copy of current bindings (for branch snapshots).
    #  @return Dict copy of bindings.
    def snapshot(self):
        return dict(self.bindings)

    ## Restore bindings from a snapshot.
    #  @param state Dict of bindings or Scope whose bindings to copy.
    def restore(self, state):
        if isinstance(state, Scope):
            self.bindings = dict(state.bindings)
        else:
            self.bindings = dict(state)


## Merge two branch snapshots with a base.
#
#  - Both unchanged from base: keep base.
#  - One branch changed, other unchanged: SourceSet([changed, base])
#    (or just changed if base had no binding for that name).
#  - Both changed to same value: keep single value.
#  - Both changed to different values: SourceSet([left, right]).
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


def _merge_two(left_binding, right_binding):
    """Create a merged binding from two different branch bindings."""
    from .sources import source_display, SourceSet as SS
    left_src = left_binding.source if isinstance(left_binding, Binding) else left_binding
    right_src = right_binding.source if isinstance(right_binding, Binding) else right_binding
    items = []
    seen = set()
    for src in (left_src, right_src):
        if isinstance(src, SS):
            for s in src.sources:
                key = source_display(s)
                if key not in seen:
                    seen.add(key)
                    items.append(s)
        elif src is not None:
            key = source_display(src)
            if key not in seen:
                seen.add(key)
                items.append(src)
    return SS(tuple(items))
