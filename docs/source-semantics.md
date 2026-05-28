# Source Semantics: IR types, SourceSet convergence, and recursion guards

This document freezes the semantics that `cross_file.py` and
`source_resolution.py` rely on.  It is not a spec for future work;
it describes the *current* behaviour that tests and baselines
enforce.

## Source IR types

| Type | Meaning | Example |
|------|---------|---------|
| `str` | Plain symbol, module path, or import alias | `"requests"`, `"np.array"` |
| `NameSource` | Explicit name wrapper | `NameSource("functools")` |
| `ContainerItem` | `container[index]` | `ContainerItem("items", 0)` |
| `ContainerIter` | `for x in container` | `ContainerIter("rows")` |
| `InstanceMethod` | `receiver.method()` | `InstanceMethod("s", "get")` |
| `CallResult` | `func()` return value | `CallResult("make")` |
| `SourceSet` | Ordered set of alternatives | `SourceSet((src1, src2))` |
| `UnknownSource` | Unresolved with display | `UnknownSource("...")` |

Legacy 3-tuples (`("container_item", a, b)`) are normalised to
dataclass objects by `normalize_source()` at the boundary.

## SourceSet.origin

The `origin` field on `SourceSet` is a hint that controls how
`SourceSetResolver.resolve_primary()` picks a primary candidate.

| origin | set by | convergence rule |
|--------|--------|------------------|
| `""` (default) | `make_source_set()` without origin | strict: all candidates must converge to the same third-party library with **no** local, unknown, or python sources present |
| `"return"` | `visit_Return` in `single_file.py` | relaxed: a single third-party candidate is accepted even when **local** sources are present, but **unknown** sources still block convergence |
| `"dict_lookup"` | dynamic-key `dict[...]` in `single_file.py` | strict: same as default — no local, no unknown, single third-party only |
| `"mixed"` | `make_source_set` flattening Sources with different origins | treated as default (strict) |

Rationale:

- **return flow** (`origin="return"`): a function like
  `def make(flag): return Local() if flag else requests.Session()`
  should surface `requests` as the primary so that `make(flag).get()`
  is not hidden as `local`.  Confidence is lowered (0.5) and `local`
  is retained in `alternatives`.

- **dict lookup** (`origin="dict_lookup"`): `items[key]` with a
  dynamic key cannot know which item is accessed.  Guessing one
  library would be a false positive.  The resolver must return
  `None` (no primary) and let the call fall back to per-source
  alternatives.

- **multi-third-party**: when a `SourceSet` contains two different
  third-party candidates (e.g. `requests.Session()` and
  `np.array()`), no primary is chosen regardless of origin.
  The system reports `top_library="local"` with alternatives
  containing both libraries.  Picking one arbitrarily would be
  a false positive.

## Recursion guard

`SourceSetResolver._to_top_candidate()` (formerly
`_source_to_top_candidate`) resolves each source in a `SourceSet`
to a top-library candidate.  For `CallResult` sources it must
**not** unconditionally call `_top_source()`, because a local
symbol whose direct binding is itself a `SourceSet` would
re-enter convergence resolution and overflow the stack.

The resolution order for `CallResult(callee=name)`:

1. **CG return source** — `_lookup_cg_return_source(module, name)`.
   If a call-graph fact records what the function returns, use it.

2. **Import-backed** — if `name.split(".")[0]` is in
   `tracer.import_aliases` or `tracer.import_from_symbols`,
   call `_top_source()` to trace the import chain.
   This is safe because import chains never produce `SourceSet`.

3. **Known local** — `_is_known_local_symbol(tracer, name)`.
   Covers `self`, `cls`, locally-defined functions/classes/methods,
   and symbols whose `direct` binding is `"local"`.
   Returns `"local"` without calling `_top_source()`.

4. **Unknown** — returns `None` (treated as `has_unknown` in
   convergence).  Does not call `_top_source()`.

A `_seen` set keyed on `(module, "cr", callee_name)` detects
cycles in the remaining layers (CG returns or import-backed
chains that circle back).

## Cross-file trace boundaries

`ProjectAnalyzer.trace_symbol()` is the entry point for
cross-module symbol tracing.  It delegates structured-source
resolution to `_resolve_structured_source()`, which dispatches
on source type.

`_resolve_structured_source()` calls `_resolve_sourceset_primary()`
for `SourceSet` inputs.  That method now delegates to
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

`classify_source()` in `cross_file.py` is the single entry point
for turning a `(base, top)` pair into a `ClassificationResult`:

| field | default | notes |
|-------|---------|-------|
| `reason` | depends on base/top | `DIRECT_IMPORT`, `RETURN_PROPAGATION`, `FLOW_MERGE`, `LOCAL_DEFINITION`, etc. |
| `confidence` | 1.0 | See `classification.py::classify_confidence()` and `docs/output-contract.md` confidence table.  local+SourceSet: 0.5; FLOW_MERGE single: 0.85; FLOW_MERGE multi: max(1/N, 0.2) |
| `alternatives` | `[]` | extracted via `_extract_alternatives()` when `expand_origins=True` |
| `is_usage_library` | `True` for third-party | controls `library_usage` aggregation |

When `top == "local"` and the base is a `SourceSet`, alternatives
are still extracted so that `library_usage` can record third-party
candidates even when the primary call classification is conservative.
