# Source Semantics

This document defines the structured source evidence consumed by ownership
resolution. These types are internal: they explain how evidence is represented
but do not become public JSON fields automatically.

## Source IR types

| Type | Meaning | Example |
|------|---------|---------|
| `str` | Plain symbol, module path, or import alias | `"requests"`, `"np.array"` |
| `NameSource` | Explicit name wrapper | `NameSource("functools")` |
| `ContainerItem` | `container[index]` | `ContainerItem("items", 0)` |
| `ContainerIter` | `for x in container` | `ContainerIter("rows")` |
| `TupleSource` | Field sources for a tuple or list element shape | `TupleSource((src1, src2))` |
| `InstanceMethod` | `receiver.method()` | `InstanceMethod("s", "get")` |
| `ParameterSource` | Value forwarded through a project-local parameter | `ParameterSource("build", "value")` |
| `InstanceAttribute` | Instance field resolved from local class and call-edge facts | `InstanceAttribute("Client", "self.session", "Client.get")` |
| `PythonShape` | Concrete Python-provided value shape | `PythonShape("list", "str")` |
| `SuperMethod` | `super().method()` with enclosing class context | `SuperMethod("Child", "Child", "get_config")` |
| `CallResult` | `func()` return value | `CallResult("make")` |
| `DerivedResult` | Result ownership derived from explicit operand semantics | `DerivedResult("element", (source,))` |
| `SourceSet` | Ordered set of alternatives | `SourceSet((src1, src2))` |
| `UnknownSource` | Unresolved with display | `UnknownSource("...")` |

`normalize_source()` also accepts compatibility tuples such as
`("container_item", a, b)` and converts them to structured source objects at
adapter boundaries.

## SourceSet.origin

The `origin` field on `SourceSet` is a hint that controls how
`SourceSetResolver.resolve_primary()` picks a primary candidate.

| origin | convergence rule |
|--------|------------------|
| `"return"` | A single non-local owner may converge when local sources are also present; unknown sources still block convergence |
| `"dict_lookup"` | Strict: one non-local owner, no local source, and no unknown source |
| all other origins, including `""`, `"function_branch"`, `"yield"`, `"builtin_element"`, `"dict_values"`, `"finite_name_selection"`, and `"mixed"` | Strict: one non-local owner, no local source, and no unknown source |

Rationale:

- **return flow** (`origin="return"`): a function like
  `def make(flag): return Local() if flag else requests.Session()`
  should surface `requests` as the primary so that `make(flag).get()`
  is not hidden as `local`. The call receives `FLOW_MERGE`, confidence
  `0.85`, and the import-backed candidate remains visible in `alternatives`.
  Local and Python labels are not emitted as library alternatives.

- **dict lookup** (`origin="dict_lookup"`): `items[key]` with a
  dynamic key cannot know which item is accessed.  Guessing one
  library would be a false positive.  The resolver must return
  `None` (no primary) and let the call fall back to per-source
  alternatives.

- **multi-library**: when a `SourceSet` contains two different
  import-backed library candidates (e.g. `requests.Session()` and
  `np.array()`), no primary is chosen regardless of origin.
  The system reports `top_library="unknown"` with alternatives
  containing both libraries.  Picking one arbitrarily would be
  a false positive.

## Recursion guard

`SourceSetResolver._to_top_candidate()` resolves each source in a `SourceSet`
to a top-level candidate. For `CallResult` sources it does not
unconditionally call `_top_source()`, because a local symbol whose direct
binding is itself a `SourceSet` would re-enter convergence resolution.

The resolution order for `CallResult(callee=name)` is:

1. **Explicit result source**: resolve `CallResult.result_source` when present.

2. **Call-graph return source**: `_lookup_cg_return_source(module, name)`.
   If a call-graph fact records what the function returns, use it.

3. **Import-backed**: if `name.split(".")[0]` is in
   `tracer.import_aliases` or `tracer.import_from_symbols`,
   call `_top_source()` to trace the import chain.
   This is safe because import chains never produce `SourceSet`.

4. **Known local**: `_is_known_local_symbol(tracer, name)`.
   Covers `self`, `cls`, locally-defined functions/classes/methods,
   and symbols whose `direct` binding is `"local"`.
   Returns `"local"` without calling `_top_source()`.

5. **Qualified import evidence**: a dotted callee can be resolved only when
   the tracer independently records import-backed evidence for it.

6. **Unknown**: returns `None` (treated as `has_unknown` in
   convergence).  Does not call `_top_source()`.

A `_seen` set keyed on `(module, "cr", callee_name)` detects
cycles in the remaining layers (CG returns or import-backed
chains that circle back).

## Cross-file trace boundaries

`ProjectAnalyzer.trace_symbol()` is implemented by
`project_source_tracing.py`. It delegates structured-source resolution to
`_resolve_structured_source()`, which dispatches on source type.

`_resolve_structured_source()` calls `_resolve_sourceset_primary()`
for `SourceSet` inputs. That method delegates to
`SourceSetResolver.resolve_primary()` in `source_resolution.py`.

The call graph:

```text
trace_symbol()
  -> _resolve_structured_source()    # dispatch on source type
       -> SourceSetResolver.resolve_primary()  # SourceSet only
            -> SourceSetResolver._collect_tops()
                 -> SourceSetResolver._to_top_candidate()
                      -> _top_source()          # import-backed only
                      -> _lookup_cg_return_source()
                      -> _is_known_local_symbol()
                      -> _resolve_structured_source()  # structured only
```

## Classification result fields

`classify_source()` in `project_call_classification.py` is the entry point for
turning a `(base, top)` pair into a `ClassificationResult`:

| field | default | notes |
|-------|---------|-------|
| `reason` | depends on base/top | `DIRECT_IMPORT`, `RETURN_PROPAGATION`, `FLOW_MERGE`, `LOCAL_DEFINITION`, etc. |
| `confidence` | 1.0 | See `classification.py::classify_confidence()` and `docs/output-contract.md` confidence table.  local+SourceSet: 0.5; FLOW_MERGE single: 0.85; FLOW_MERGE multi: max(1/N, 0.2) |
| `alternatives` | `[]` | extracted via `_extract_alternatives()` when `expand_origins=True` |
| `is_usage_library` | `True` for import-backed library | controls `library_usage` aggregation |

When `top == "local"` and the base is a `SourceSet`, alternatives
are still extracted so that `library_usage` can record import-backed library
candidates even when the primary call classification is conservative.
