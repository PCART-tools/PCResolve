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

Rule priority order:

1. Local function/method definition → `"local"`
2. Python builtin / implicit builtin (no import required) → `"python"`
3. Imported stdlib module (via import/from import) → top-level module name
4. Imported third-party module (via import/from import) → top-level package name
5. Cross-file re-export → library name
6. Parameter propagation → library name, confidence < 1.0
7. Return value propagation → library name, confidence < 1.0
8. Branch/fork multi-source → alternatives, confidence < 1.0
9. Unresolved → `"unknown"`, `REASON_UNRESOLVED`

Compatibility note: in the current pre-8B implementation, unresolved non-builtin
symbols may retain their raw symbol name as the `top_library` (e.g. an
undefined/global/dynamic symbol whose chain resolution falls through).
Phase 8B should normalise all unresolved cases to `"unknown"` with
`REASON_UNRESOLVED`.

## Reason Constants (Phase 8A)

| Constant | Meaning |
|----------|---------|
| `DIRECT_IMPORT` | Symbol is an import alias or from-import |
| `TRANSITIVE_IMPORT` | Symbol traces through a re-export chain |
| `LOCAL_DEFINITION` | Symbol resolves to a locally defined function/class |
| `BUILTIN` | Symbol is a Python builtin (no import required) |
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
- `return_sources` is SourceSet since Phase 5; multiple return paths are collected but alternatives classification is not yet complete.
- Constructor argument to `self.attr` propagation and wrapper-class instance method resolution is handled by 7B-lite via `instance_attrs`, `CallResult.call_lineno`, and constructor call-site matching. Full CallGraph / return-object tracking for factory-returned instances is deferred to complete 7B.
- `nonlocal` is first-edition no-crash only.

## Phase 7B-lite: Class / Instance Method Resolution

7B-lite is the engineering transition layer before full 7B / CallGraph.  It
extends existing `InstanceMethod`, `CallResult.call_lineno/call_col_offset`,
`return_sources`, and constructor call-site facts to handle the most common
wrapper-class patterns without introducing a full class hierarchy graph.

### Supported

| Pattern | Example | Resolution |
|---------|---------|------------|
| Instance method on locally-constructed object | `x = ClassName(...); x.method(...)` | `InstanceMethod(receiver=x, method=method)` |
| Wrapper method return-source through constructor arg | `api = Api(requests.Session()); api.get(...)` | `requests` |
| Multi-instance receiver-specific constructor matching | `a = Api(requests.Session()); b = Api(httpx.Client())` | `a.get()` → `requests`, `b.get()` → `httpx` |
| Simple alias following | `c = b; c.get(...)` | follows to same constructor call-site |
| `self.attr.method()` in method body | `self.session = param; ... return self.session.get(...)` | participates in return-source propagation |
| Pure-local method | no constructor-arg dependency | `"local"` |

### Conservative Boundaries

- **Factory-returned instances**: `c = make(httpx.Client()); c.get(...)` →
  `"local"`.  Requires full CallGraph / return-object tracking.
- **Method name collision / override**: `return_sources` is keyed by bare
  method name (e.g. `"get"`).  Complex same-name methods, inheritance,
  and overrides need `Class.method` / `FunctionId(module, qualname)` in
  full 7B.
- **Third-party base-class methods, `@classmethod`, `@staticmethod`,
  descriptors / properties**: not in lite scope.

### Minimal Examples

```python
import requests, httpx

class Api:
    def __init__(self, session):
        self.session = session
    def get(self, url):
        return self.session.get(url)

a = Api(requests.Session())
b = Api(httpx.Client())
c = make(httpx.Client())          # factory — not supported in lite

a.get("x")   # → requests
b.get("y")   # → httpx
c.get("z")   # → local  (known limitation)
```

### Relationship to Phase 8C Decorator Semantics

7B-lite does **not** alter the decorator provenance contract established by
8C / 8C+:

- Decorator evidence continues to be exposed via `decorated_by`.
- A decorator never changes the primary identity of the decorated target.
- `ApiCall.decorated_by` exact-match (file_path, scope, func_name) is
  unchanged; method-call `decorated_by` remains deferred to full 7B
  class-aware resolution.

## Phase 8C: Decorator Provenance Semantics

Decorators create two distinct kinds of evidence that must not be conflated:

| Evidence | Field | Semantics | Stability |
|----------|-------|-----------|-----------|
| Decorator expression call | `ApiCall.top_library` | The decorator `@lib.deco(args)` itself is a call to `lib` | Public, stable |
| Decorated target call | `ApiCall.top_library` | A call to the decorated function/class is **always** `"local"` | Public, stable |
| Decorator provenance evidence | `SymbolProvenance(kind="decorated_by")` | Records which libraries decorated the target | Public, stable |
| Decorator evidence on call | `ApiCall.decorated_by` | Mirrors `decorated_by` evidence onto matching calls by exact `func_name` match (file_path, func_name) | Public, additive-only; method calls require Phase 7B |

### Core Invariant

> **A decorator never changes the primary identity of the decorated target.**  
> `@app.route("/")` makes `index()` a Flask-decorated function, but `index()` itself is still a locally-defined callable.  
> Its `top_library` remains `"local"`. Decorator provenance is surfaced via `decorated_by`, not via `top_library`.

### Decorator Identity Preservation (Phase 8C+)

Local decorator functions preserve their name as evidence, and chain through `return_sources`:

| Decorator | `decorated_by` evidence |
|-----------|------------------------|
| `@app.route("/")` | `flask` |
| `@click.command()` | `click` |
| `@dataclass` | `dataclasses` |
| `@local_deco` (returns `click.command()(f)`) | `click` (via `return_sources`) |
| `@passthrough` (returns `f`) | `"local"` (filtered from `ApiCall.decorated_by`) |

### Consumer Guidance (PCART / downstream)

To find all call sites potentially related to library `lib`:

1. **Direct API calls**: `ApiCall.top_library == lib`
2. **Decorated local calls**: `lib in ApiCall.decorated_by` AND `ApiCall.top_library == "local"`
3. **Method calls**: currently only in `SymbolProvenance(kind="decorated_by")`; Phase 7B will add class-aware `ApiCall.decorated_by` for methods

### `ApiCall.decorated_by` Contract

- **Field type**: `list[str]`, default `[]`
- **Stability**: additive-only (new evidence may appear, but existing entries never removed without schema version bump)
- **Null/empty semantics**: `[]` means "no decorator evidence found on this call" (may be a false negative for method calls pre-7B)
- **Filtered values**: `"local"`, `"python"`, `"unknown"` are excluded; only import-backed library names appear
- **Matching**: exact match on `(file_path, func_name)` where `func_name` is the call's bare function name (e.g. `"index"` for `index()`, not `"c.method"` for method calls)

## Phase 5 / 7A / 7B / 8B Contracts

- **Phase 5** must not add classification logic in `_base_top_source()`. Instead, `SourceSet` alternatives should flow through `TraceResult.tops` and be classified by the pipeline.
- **Phase 7A** should produce `CallGraph` edges that feed into `TraceResult` as the authoritative param/return propagation source, not as a third parallel path.
- **Phase 7B** should replace `instance_attrs` with systematic class method resolution through the call graph.
- **Phase 8B** should migrate `extract_final_source()` and `_base_top_source()` into `ClassificationPipeline` rules.
