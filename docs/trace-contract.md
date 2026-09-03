# PCResolve Trace Contract

## Core Principle

> **Trace produces facts. Classify makes decisions.**

These are distinct responsibilities with different stability guarantees.

## Trace Pipeline

```
Source IR (single_file.py)
  → source chains and candidate owners (cross_file.py)
  → Classification (classification.py: ClassificationPipeline)
  → ApiCall / SymbolProvenance (cross_file.py)
```

### Trace Responsibilities

1. Given a symbol or call expression, produce an ordered chain of source references from the definition site to the ultimate origin.
2. Report when the trace is incomplete (e.g., recursion limit, unresolvable structured source).
3. Provide all candidate origins when the trace splits (via `SourceSet`).
4. Keep source resolution separate from final reason, confidence, and
   alternatives assignment. Compatibility helpers may compute temporary top
   owner values, but `ClassificationPipeline` creates the final classification.

### Classify Responsibilities

1. Given the resolved base source and candidate top owner, determine the final
   `top_library` using `ClassificationPipeline.classify()`.
2. Assign `reason`, `confidence`, and `alternatives`.
3. Handle ambiguous cases (multiple candidates, local + import-backed mixed) explicitly.
4. Unresolved cases produce `top_library = "unknown"` with `reason = "UNRESOLVED"`.

## Current State (1.0.5)

`classify_source()` in `cross_file.py` delegates to `ClassificationPipeline.classify()`
in `classification.py`, which applies priority-ordered rules:

| Location | Role |
|----------|------|
| `extract_final_source()` (cross_file.py) | Walks chain reverse, returns ultimate source string |
| `_base_top_source()` (cross_file.py) | Resolves structured sources, delegates to `_top_source()` |
| `get_calls()` (cross_file.py) | Collects and classifies every API call through the pipeline |
| `ClassificationPipeline.classify()` (classification.py) | Priority-ordered reason, confidence, alternatives assignment |

## TraceResult Data Model

`TraceResult` is the typed result model for a fully separated trace boundary.
The 1.0.5 project pipeline still passes resolved `(base, top)` values directly
to `ClassificationPipeline`, so this dataclass is not the sole runtime path.

| Field | Source | Semantics |
|-------|--------|-----------|
| `source` | `SymbolRef.source` or `CallSite.base` | Original source object |
| `chain` | `trace_symbol()` output | Ordered display chain, dedup'd |
| `tops` | `extract_final_source()` | Candidate top-level owners; may contain multiple alternatives |
| `complete` | Trace outcome | Whether trace reached a terminal without errors |
| `diagnostics` | Trace errors | Recursion limit, cycle detection, etc. |

## Classification Pipeline

Final classification priority order:

1. A resolved local definition produces `"local"`.
2. A Python-provided builtin or value shape produces `"python"`.
3. An empty or unresolved owner produces `"unknown"`.
4. A direct import produces its import-backed top-level owner.
5. A `SourceSet` base produces `FLOW_MERGE` and preserves import-backed
   alternatives.
6. A `CallResult`, including one used as an instance-method receiver, produces
   `RETURN_PROPAGATION` unless multiple concrete owners require `FLOW_MERGE`.
7. Other resolved import chains produce `TRANSITIVE_IMPORT`.

Parameter tracing participates in candidate-owner resolution before this final
step. `PARAMETER_PROPAGATION` remains a stable reason constant, while current
1.0.5 call classifications commonly expose the terminal reason from the
resolved import, return, or flow merge.

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

## Confidence Rules

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

- Parameter and return propagation uses exact call-site positions and a unique
  project-local target. Ambiguous targets, conflicting owners, unsupported
  argument binding, and recursive cycles remain `unknown`.
- `return_sources` uses `SourceSet` for multi-return paths; alternatives classification handles ambiguous cases.
- Constructor argument to `self.attr` propagation and wrapper-class instance
  method resolution uses `instance_attrs` and constructor call-site matching.
  `_resolve_receiver_object_top` handles statically supported factory-returned
  instances; complex factories with branches or unresolved returns remain
  conservative.
- `nonlocal` declarations are parsed without failure; assignment routing to an
  enclosing function scope is not currently modeled.

## Bounded Local Call Propagation

PCResolve performs context-sensitive propagation across a unique
project-local call edge. The context is identified by the caller module and
the exact call line and column. Positional and keyword arguments can replace
the callee's parameters while resolving:

- a parameter used as a receiver inside a local function;
- a local function result returned from one or more simple wrappers;
- a constructor argument stored on `self` and returned by a local method;
- the same local function called with different owners at different call
  sites.

Each context is evaluated independently. Reusing the same assignment name at
later call sites does not change earlier results. A return summary with one
owner produces `RETURN_PROPAGATION`; multiple concrete owners produce
`FLOW_MERGE` with alternatives and an `unknown` primary owner.

This is a bounded, context-sensitive project call graph, not complete Python
runtime reconstruction. PCResolve does not guess through unresolved dynamic
dispatch, unresolved callbacks, arbitrary mutation, external library
implementations, or dead code without a statically supported value.

### Literal Callback Tables

Nested literal dictionaries retain local callable identities through aliases,
subscripts and builtin `dict.get` selection:

```python
registry = {'module': {'run': consume}}
callback = registry['module'].get('run')
callback(options)
```

The selected callable can connect a local call edge and propagate arguments.
It does not make the dictionary or its other values share that callable's
owner. Unknown keys retain possible local targets, not a unique return
context. Mixed or unresolved alternatives cannot establish an exact return
context either.

Mutation, escaping containers and deferred module rebindings invalidate the
supporting facts, including aliases. Closure captures and mappings rebound
across unsupported control-flow joins remain conservative. These are private
analysis facts and add no fields to the public output contract.

### Return Shapes in Parameter Forwarding

Method queries through local parameter forwarding use concrete return-value
facts separately from symbol provenance. Explicit scalar and `None` returns
are retained alongside container returns. A possible fall-through return also
prevents the remaining branch from being treated as an unconditional result.

For example, passing a function result that can be either a dictionary or an
integer to `consume(value)` does not prove that `value.get(...)` is a Python
method. Every retained alternative must support the requested protocol.
Cross-file wrappers and nested local functions preserve their exact call
contexts; recursive or unresolved alternatives remain conservative.

An `__init__` return does not describe the instance produced by a constructor.
Likewise, a returned tuple and its unpacked items are distinct. These private
facts neither change public JSON fields nor infer external return types.

### Returned Iterable Elements

The owner of a returned container is separate from the owners of its elements.
For a local `pack(value): return [value]`, iteration over `pack(argument)`
substitutes that call's argument into the returned-element source. This also
applies across modules, local method calls, simple return wrappers, and wrappers
returning a local generator. Generator elements come from `yield`, not `return`.

Different call sites remain independent. Concrete Python element shapes are
preserved so a returned string can support `strip()` without being assumed to
support `append()`. Conflicting branches, unresolved elements, and recursive
cycles remain `unknown`. Rebinding a loop variable ends the earlier evidence.
This path does not infer an external iterable's element owner from its
container owner.

## Class and Instance Method Resolution

PCResolve handles common wrapper-class patterns using `InstanceMethod`,
`CallResult.call_lineno/call_col_offset`, `return_sources`, exact
`FunctionId(module, qualname)` targets, and constructor call-site facts. The
resolver follows bounded local inheritance without claiming a complete Python
class hierarchy.

### Supported

| Pattern | Example | Resolution |
|---------|---------|------------|
| Instance method on locally-constructed object | `x = ClassName(...); x.method(...)` | `InstanceMethod(receiver=x, method=method)` |
| Wrapper method return-source through constructor arg | `api = Api(requests.Session()); api.get(...)` | `requests` |
| Multi-instance receiver-specific constructor matching | `a = Api(requests.Session()); b = Api(httpx.Client())` | `a.get()` → `requests`, `b.get()` → `httpx` |
| Simple alias following | `c = b; c.get(...)` | follows to same constructor call-site |
| `self.attr.method()` in method body | `self.session = param; ... return self.session.get(...)` | participates in return-source propagation |
| Exact local `@classmethod` or `@staticmethod` target | `Worker.consume(value)` | aligns bound and explicit arguments with the method signature |
| Pure-local method | no constructor-arg dependency | `"local"` |

### Conservative Boundaries

- **Factory-returned instances**: simple local factories that return a
  import-backed library-owned object (e.g. `def make(): return requests.Session()`) are
  supported. Factories with unresolved branches, mutation, or ambiguous call
  targets remain conservative.
- **Method collisions and overrides**: exact local targets use
  `FunctionId(module, qualname)`, and a nearest local inherited implementation
  can be selected. Multiple-inheritance siblings remain explicit alternatives
  when one target cannot be proven.
- **Import-backed base classes**: a directly imported, statically named base can
  establish the owner of an inherited method. Full external MRO, metaclasses,
  dynamic descriptors, and properties are not modeled.

### Minimal Examples

```python
import requests, httpx

def make(client):
    return client

class Api:
    def __init__(self, session):
        self.session = session
    def get(self, url):
        return self.session.get(url)

a = Api(requests.Session())
b = Api(httpx.Client())
c = make(httpx.Client())          # statically supported factory return

a.get("x")   # → requests
b.get("y")   # → httpx
c.get("z")   # → httpx
```

### Relationship to Decorator Provenance

Class method resolution does **not** alter the decorator provenance contract:

- Decorator evidence continues to be exposed via `decorated_by`.
- A decorator never changes the primary identity of the decorated target.
- `ApiCall.decorated_by` uses two-level matching:
  exact `(file_path, scope_name, func_name)` with receiver-aware fallback
  for dotted calls.  Instance methods on decorated classes still require
  full class-aware resolution.

## Decorator Provenance Semantics

Decorators create two distinct kinds of evidence that must not be conflated:

| Evidence | Field | Semantics | Stability |
|----------|-------|-----------|-----------|
| Decorator expression call | `ApiCall.top_library` | The decorator `@lib.deco(args)` itself is a call to `lib` | Public, stable |
| Decorated target call | `ApiCall.top_library` | A call to the decorated function/class is **always** `"local"` | Public, stable |
| Decorator provenance evidence | `SymbolProvenance(kind="decorated_by")` | Records which libraries decorated the target | Public, stable |
| Decorator evidence on call | `ApiCall.decorated_by` | Mirrors `decorated_by` evidence via two-level match: exact `(file_path, scope_name, func_name)` then receiver-aware fallback for dotted calls | Public, additive-only |

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
3. **Method calls**: decorated callable receiver methods (e.g. `hello.main()`)
   use receiver-aware lookup. Full class-aware receiver resolution for instance
   methods on decorated classes is not currently modeled.

### `ApiCall.decorated_by` Contract

- **Field type**: `list[str]`, default `[]`
- **Stability**: additive-only (new evidence may appear, but existing entries never removed without schema version bump)
- **Null/empty semantics**: `[]` means "no decorator evidence found on this call". Receiver-aware lookup supports dotted method calls (e.g. `hello.main()`); instance methods on decorated classes require full class-aware resolution.
- **Filtered values**: `"local"`, `"python"`, `"unknown"` are excluded; only import-backed library names appear
- **Matching**: two-level lookup:
  1. exact: `(file_path, scope_name, func_name)`
  2. receiver-aware fallback: if `func_name` is dotted,
     match the first dot-segment as the receiver in the decorator index
  Supported: `hello.main()` where `hello` has `decorated_by` provenance.
  Not yet supported: instance methods on decorated classes, MRO-based
  receiver resolution, aliased receivers (e.g. `cmd = hello; cmd.main()`).

### Decorated Callable Receiver Methods

Calls such as `hello.main()` where `hello` is a local function decorated by
`@click.command()` are classified as `local`.  This is intentional:
the decorated callable remains a same-project object, so decorator evidence
must not replace the primary `top_library`.

Receiver-aware `decorated_by` lookup applies when `func_name` is
dotted (e.g. `hello.main`), `lookup_decorated_by` also checks the receiver
part (`hello`) in the decorator index.  This means `hello.main().decorated_by`
now contains `["click"]` while `top_library` stays `local`.

Receivers are identified by the first dot-segment of `func_name`; the
lookup does NOT guess libraries from method names like `main`, `run`,
or `callback`.

Contract points:

- `hello.main()` continues to report `top_library="local"`.
- Decorated local callables are not reclassified as import-backed primary calls.
- Receiver-aware lookup propagates `decorated_by` from the
  decorated callable to its dotted method calls (e.g. `hello.main()`).
- Full class-aware decorated instance methods are not currently modeled.
- Downstream consumers should inspect both `SymbolProvenance(kind="decorated_by")`
  and `ApiCall.decorated_by`.

## Remaining Boundaries

- **SourceSet alternatives**: flow through `ClassificationPipeline` for multi-source resolution.
- **CallGraph edges**: `call_graph.py` feeds param/return propagation into trace.
- **Class method resolution**: `instance_attrs`, exact local function targets,
  and bounded inheritance handle supported constructor and method flows. Full
  Python MRO, metaclass behavior, and dynamic descriptors are not modeled.
- **Classification**: `ClassificationPipeline.classify()` handles reason/confidence/alternatives.
- **Method decorator evidence**: `ApiCall.decorated_by` uses exact
  `(file_path, scope_name, func_name)` matching plus receiver-aware fallback
  for dotted decorated callable calls; full class-aware decorated instance
  methods are not currently modeled.
