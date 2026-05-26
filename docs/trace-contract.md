# PCResolve Trace Contract

## Core Principle

> **Trace produces facts. Classify makes decisions.**

These are distinct responsibilities with different stability guarantees.

## Trace Pipeline (Ideal)

```
Source IR (single_file.py)
  → TraceResult (cross_file.py: trace_symbol)
  → Classification (classifier.py, future Phase 8B)
  → ApiCall / SymbolProvenance (cross_file.py)
```

### Trace Responsibilities

1. Given a symbol or call expression, produce an ordered chain of source references from the definition site to the ultimate origin.
2. Report when the trace is incomplete (e.g., recursion limit, unresolvable structured source).
3. Provide all candidate origins when the trace splits (via `SourceSet`, Phase 5).
4. Never assign a `top_library` directly — that is the classifier's job.

### Classify Responsibilities

1. Given a `TraceResult`, determine the `top_library` using a priority-ordered rule pipeline.
2. Assign `reason`, `confidence`, and `alternatives`.
3. Handle ambiguous cases (multiple candidates, local + third-party mixed) explicitly.
4. Unresolved cases produce `library = "unknown"` with `reason = "UNRESOLVED"`.

## Current State (Pre-Phase 8B)

In the current implementation, trace and classify are **coupled** in several places:

| Location | Mixed Concern |
|----------|--------------|
| `extract_final_source()` (cross_file.py) | Walks chain reverse, checks `is_local`, returns `"python"` for builtins — classification inline with trace |
| `_base_top_source()` (cross_file.py) | Resolves structured sources and determines `top` — classification inline with resolution |
| `get_calls()` (cross_file.py) | Checks `top == 'local'` and re-resolves — classification inline with call collection |
| `_one_api_call()` (single_file.py) | Sets `top` directly from `trace_source` results — classification in AST visitor |

## TraceResult Fields

| Field | Source | Semantics |
|-------|--------|-----------|
| `source` | `SymbolRef.source` or `CallSite.base` | Original source object |
| `chain` | `trace_symbol()` output | Ordered display chain, dedup'd |
| `tops` | `extract_final_source()` | Current: single top string. Future: list with alternatives |
| `complete` | Trace outcome | Whether trace reached a terminal without errors |
| `diagnostics` | Trace errors | Recursion limit, cycle detection, etc. |

## Classification Pipeline (Phase 8A/8B)

Rule priority order (from Plans.md):

1. Local function/method definition → `"local"`
2. Python builtin / stdlib → `"python"`
3. Direct third-party import → library name
4. Cross-file re-export → library name
5. Parameter propagation → library name, confidence < 1.0
6. Return value propagation → library name, confidence < 1.0
7. Branch/fork multi-source → alternatives, confidence < 1.0
8. Unresolved → `"unknown"`, `REASON_UNRESOLVED`

## Reason Constants (Phase 8A)

| Constant | Meaning |
|----------|---------|
| `DIRECT_IMPORT` | Symbol is an import alias or from-import |
| `TRANSITIVE_IMPORT` | Symbol traces through a re-export chain |
| `LOCAL_DEFINITION` | Symbol resolves to a locally defined function/class |
| `BUILTIN` | Symbol is a Python builtin |
| `PARAMETER_PROPAGATION` | Symbol traces through a function parameter |
| `RETURN_PROPAGATION` | Symbol traces through a function return value |
| `FLOW_MERGE` | Multiple branches merged (if/else, try/except) |
| `UNRESOLVED` | Trace could not reach a terminal |

## Confidence Rules (First Edition)

| Case | Confidence |
|------|------------|
| Single direct import | 1.0 |
| Single local definition | 1.0 |
| Single builtin | 1.0 |
| Parameter propagation, unique source | 0.9 |
| Return propagation, unique source | 0.9 |
| Multiple sources, same library | 0.85 |
| Multiple sources, multiple libraries | `1 / len(alternatives)`, min 0.2 |
| Unresolved | 0.0 |

## Known Limitations

- Trace does not distinguish "parameter from call site A" vs "parameter from call site B" when a function is called from multiple locations. Resolution picks the first matching call site.
- `return_sources` is single-valued; multiple return paths are lost.
- Constructor argument to `self.attr` propagation is ad-hoc (via `instance_attrs`), not integrated with call graph.
- `nonlocal` is first-edition no-crash only.

## Phase 5 / 7A / 7B / 8B Contracts

- **Phase 5** must not add classification logic in `_base_top_source()`. Instead, `SourceSet` alternatives should flow through `TraceResult.tops` and be classified by the pipeline.
- **Phase 7A** should produce `CallGraph` edges that feed into `TraceResult` as the authoritative param/return propagation source, not as a third parallel path.
- **Phase 7B** should replace `instance_attrs` with systematic class method resolution through the call graph.
- **Phase 8B** should migrate `extract_final_source()` and `_base_top_source()` into `ClassificationPipeline` rules.
