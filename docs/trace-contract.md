# PCResolve Trace Contract

## Core Principle

> **Trace produces facts. Classify makes decisions.**

These are distinct responsibilities with different stability guarantees.

## Trace Pipeline (Ideal)

```
Source IR (single_file.py)
  → TraceResult (cross_file.py: trace_symbol)
  → Classification (classification.py: ClassificationPipeline)
  → ApiCall / SymbolProvenance (cross_file.py)
```

### Trace Responsibilities

1. Given a symbol or call expression, produce an ordered chain of source references from the definition site to the ultimate origin.
2. Report when the trace is incomplete (e.g., recursion limit, unresolvable structured source).
3. Provide all candidate origins when the trace splits (via `SourceSet`).
4. Never assign a `top_library` directly — that is the classifier's job.

### Classify Responsibilities

1. Given a `TraceResult`, determine the `top_library` using `ClassificationPipeline.classify()`.
2. Assign `reason`, `confidence`, and `alternatives`.
3. Handle ambiguous cases (multiple candidates, local + third-party mixed) explicitly.
4. Unresolved cases produce `library = "unknown"` with `reason = "UNRESOLVED"`.

## Current State (1.0.4)

`classify_source()` in `cross_file.py` delegates to `ClassificationPipeline.classify()`
in `classification.py`, which applies priority-ordered rules:

| Location | Role |
|----------|------|
| `extract_final_source()` (cross_file.py) | Walks chain reverse, returns ultimate source string |
| `_base_top_source()` (cross_file.py) | Resolves structured sources, delegates to `_top_source()` |
| `get_calls()` (cross_file.py) | Collects and classifies every API call through the pipeline |
| `ClassificationPipeline.classify()` (classification.py) | Priority-ordered reason, confidence, alternatives assignment |

## TraceResult Fields

| Field | Source | Semantics |
|-------|--------|-----------|
| `source` | `SymbolRef.source` or `CallSite.base` | Original source object |
| `chain` | `trace_symbol()` output | Ordered display chain, dedup'd |
| `tops` | `extract_final_source()` | Current: single top string. Future: list with alternatives |
| `complete` | Trace outcome | Whether trace reached a terminal without errors |
| `diagnostics` | Trace errors | Recursion limit, cycle detection, etc. |

## Classification Pipeline

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

Unresolved symbols are normalised to `"unknown"` with `REASON_UNRESOLVED`
by `ClassificationPipeline.classify()`.

## Reason Constants

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

- Parameter propagation uses `CallResult.call_lineno/call_col_offset` and receiver constructor call-site matching for disambiguation. Multi-call-site scenarios may still produce merged alternatives.
- `return_sources` uses `SourceSet` for multi-return paths; alternatives classification handles ambiguous cases.
- Constructor argument to `self.attr` propagation and wrapper-class instance method resolution uses `instance_attrs` and constructor call-site matching. Factory-returned instances require full return-object tracking (future work).
- `nonlocal` is first-edition no-crash only.

## Class and Instance Method Resolution

PCResolve handles common wrapper-class patterns using `InstanceMethod`,
`CallResult.call_lineno/call_col_offset`, `return_sources`, and constructor
call-site facts, without a full class hierarchy graph.

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
  `"local"`.  Requires full CallGraph / return-object tracking (future work).
- **Method name collision / override**: `return_sources` is keyed by bare
  method name (e.g. `"get"`).  Complex same-name methods, inheritance,
  and overrides need `Class.method` / `FunctionId(module, qualname)`
  (future work).
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

### Relationship to Decorator Provenance

Class method resolution does **not** alter the decorator provenance contract:

- Decorator evidence continues to be exposed via `decorated_by`.
- A decorator never changes the primary identity of the decorated target.
- `ApiCall.decorated_by` exact-match (file_path, scope, func_name) is
  unchanged; method-call `decorated_by` depends on future full class-aware
  receiver resolution.

## Decorator Provenance Semantics

Decorators create two distinct kinds of evidence that must not be conflated:

| Evidence | Field | Semantics | Stability |
|----------|-------|-----------|-----------|
| Decorator expression call | `ApiCall.top_library` | The decorator `@lib.deco(args)` itself is a call to `lib` | Public, stable |
| Decorated target call | `ApiCall.top_library` | A call to the decorated function/class is **always** `"local"` | Public, stable |
| Decorator provenance evidence | `SymbolProvenance(kind="decorated_by")` | Records which libraries decorated the target | Public, stable |
| Decorator evidence on call | `ApiCall.decorated_by` | Mirrors `decorated_by` evidence onto matching calls by exact `(file_path, scope_name, func_name)` match | Public, additive-only; method calls require future class-aware resolution |

### Core Invariant

> **A decorator never changes the primary identity of the decorated target.**  
> `@app.route("/")` makes `index()` a Flask-decorated function, but `index()` itself is still a locally-defined callable.  
> Its `top_library` remains `"local"`. Decorator provenance is surfaced via `decorated_by`, not via `top_library`.

### Decorator Identity Preservation

Local decorator functions preserve their name as evidence, and chain through `return_sources`:

| Decorator | `decorated_by` evidence |
|-----------|------------------------|
| `@app.route("/")` | `flask` |
| `@click.command()` | `click` |
| `@dataclass` | `dataclasses` |
| `@local_deco` (returns `click.command()(f)`) | `click` (via `return_sources`) |
| `@passthrough` (returns `f`) | `"local"` (filtered from `ApiCall.decorated_by`) |

### Downstream Consumer Guidance

To find all call sites potentially related to library `lib`:

1. **Direct API calls**: `ApiCall.top_library == lib`
2. **Decorated local calls**: `lib in ApiCall.decorated_by` AND `ApiCall.top_library == "local"`
3. **Method calls**: currently only in `SymbolProvenance(kind="decorated_by")`; `ApiCall.decorated_by` for methods depends on future full class-aware receiver resolution

### `ApiCall.decorated_by` Contract

- **Field type**: `list[str]`, default `[]`
- **Stability**: additive-only (new evidence may appear, but existing entries never removed without schema version bump)
- **Null/empty semantics**: `[]` means "no decorator evidence found on this call" (may be a false negative for method calls before full class-aware matching)
- **Filtered values**: `"local"`, `"python"`, `"unknown"` are excluded; only import-backed library names appear
- **Matching**: exact match on `(file_path, scope_name, func_name)` where
  `func_name` is the call's bare function name (e.g. `"index"` for `index()`)
  and `scope_name` disambiguates module-level, nested, and class scopes.
  Method calls still require full class-aware receiver resolution before
  `decorated_by` can be attached reliably.

### Decorated Callable Receiver Methods

Calls such as `hello.main()` where `hello` is a local function decorated by
`@click.command()` are currently classified as `local`.  This is intentional:
the decorated callable remains a same-project object, so decorator evidence
must not replace the primary `top_library`.

Decorator provenance is recorded on the decorated symbol.  Receiver-method
calls such as `hello.main()` may require receiver-aware matching before
that evidence can be mirrored into `ApiCall.decorated_by`.

Until that matching exists, consumers that need this association should
inspect `SymbolProvenance(kind="decorated_by")` in addition to
`ApiCall.decorated_by`.

Contract points:

- `hello.main()` continues to report `top_library="local"`.
- Decorated local callables are not reclassified as third-party primary calls.
- The current boundary is that `decorated_by` is not propagated to receiver
  method calls.
- Downstream consumers should inspect both `SymbolProvenance(kind="decorated_by")`
  and `ApiCall.decorated_by`.

## Remaining Boundaries

- **SourceSet alternatives**: flow through `ClassificationPipeline` for multi-source resolution.
- **CallGraph edges**: `call_graph.py` feeds param/return propagation into trace.
- **Class method resolution**: `instance_attrs` handles constructor args; full class-aware receiver resolution (MRO, `@classmethod`, `@staticmethod`) is future work.
- **Classification**: `ClassificationPipeline.classify()` handles reason/confidence/alternatives.
- **Method decorator evidence**: `ApiCall.decorated_by` matches by `(file_path, scope_name, func_name)`; class-aware receiver resolution is future work.
