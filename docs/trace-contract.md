# PCResolve Trace Contract

## Core invariant

> **Trace produces evidence. Classification makes the ownership decision.**

Tracing follows definitions, bindings, call contexts, returns, attributes, and
containers. Classification converts the resolved evidence into the stable
`top_library`, `reason`, `confidence`, and `alternatives` fields. Neither stage
may invent an owner from a variable name, method name, project name, or
unverified library convention.

## Trace pipeline

```text
CallSite / SymbolRef and structured source evidence
  → project_source_tracing.py
  → call, result, container, and receiver resolvers
  → project_call_classification.py
  → classification.py
  → ApiCall / SymbolProvenance
```

Tracing must:

- preserve an ordered explanation chain;
- retain all supported alternatives when control flow or data flow splits;
- use exact module, scope, and source-position identity for local calls;
- stop recursive imports, calls, assignments, and structured sources with
  explicit guards;
- return incomplete or unresolved evidence when a boundary is reached.

Classification must:

- emit an import-backed top-level name only when import or propagated source
  evidence supports it;
- classify proven Python-provided callables and value shapes as `python`;
- preserve project-defined callable identity as `local`;
- emit `unknown` when no unique supported primary owner exists;
- keep additional import-backed candidates in `alternatives`.

The exact public fields, reason constants, and confidence rules are defined in
[Output Contract](output-contract.md). Structured source meanings and
`SourceSet` convergence are defined in
[Source Semantics](source-semantics.md).

## Bounded local call propagation

PCResolve propagates ownership through a unique project-local call target. A
call context is identified by the caller, callee definition, and exact call
position. Positional, keyword, default, variadic, and implicit receiver
bindings are applied only when the supported binding facts establish them.

Supported propagation includes:

- parameters used as receivers inside local functions and methods;
- values returned through local wrappers;
- distinct owners supplied to the same function at different call sites;
- constructor arguments stored on `self` and read by local methods;
- callback identities selected from supported literal containers;
- iterable elements returned by local functions and generators;
- concrete Python value shapes carried through supported local calls.

Each call context remains independent. A later assignment or call does not
rewrite an earlier call's evidence. Conflicting owners, ambiguous targets,
unsupported expansion, and recursion remain conservative.

This is not complete Python runtime reconstruction. PCResolve does not infer
through arbitrary callback behavior, dynamic dispatch, external function
bodies, or unsupported mutation.

## Returns and containers

Return ownership is separate from callable ownership. `CallResult` identifies
the producing call and may carry an independently resolved result source.
Multiple return paths form an ordered `SourceSet`; convergence follows the
rules in `source_resolution.py`.

Container ownership is also distinct from element ownership:

- `ContainerItem` represents selection from an indexed or keyed container;
- `ContainerIter` represents an element produced by iteration;
- `TupleSource` preserves field sources for supported unpacking;
- returned containers retain separate container and element evidence;
- unknown keys, dynamic lengths, or conflicting element sources do not select
  one owner arbitrarily.

For a local `pack(value): return [value]`, iteration over `pack(argument)` can
substitute that call's argument into the returned-element source. The same rule
applies to supported local wrappers and generators. It does not infer an
external iterable's element owner from the container owner.

## Callback selection

Nested literal dictionaries can retain project-local callable identities
through aliases, subscripts, and supported `dict.get` selection:

```python
registry = {"module": {"run": consume}}
callback = registry["module"].get("run")
callback(options)
```

An exact selected callable can create a local call context. Unknown keys retain
possible targets rather than selecting one. Mutation, escape, deferred module
rebinding, or unsupported control-flow joins invalidate the exact selection.

## Class and instance methods

PCResolve resolves common local wrapper-class patterns using exact
`FunctionId(module, qualname)` targets, constructor call positions, instance
field facts, return summaries, and bounded inheritance.

| Pattern | Result |
|---|---|
| Method on a locally constructed object | Uses the exact local class/method target when available |
| Constructor argument stored on `self` | Can propagate the argument owner to later field receivers |
| Multiple instances with different constructor arguments | Keeps receiver-specific call contexts separate |
| Simple receiver alias | Follows the same constructor identity |
| Exact local classmethod or staticmethod | Aligns implicit and explicit parameters with the method signature |
| Simple local factory returning an owned object | Propagates the supported result owner |
| Pure local method | Remains `local` |

Nearest supported local inherited implementations can be selected. Ambiguous
multiple inheritance remains a set of candidates. A directly imported,
statically named external base can establish an inherited method owner, but
PCResolve does not model a complete external MRO, metaclasses, dynamic
descriptors, or arbitrary properties.

## Decorator provenance

Decorator ownership and decorated-target ownership are separate facts.

| Evidence | Public representation |
|---|---|
| Decorator expression call | Its own `ApiCall.top_library` |
| Call to a decorated local function or class | `top_library="local"` |
| Libraries that decorated the target | `SymbolProvenance(kind="decorated_by")` and `ApiCall.decorated_by` |

The invariant is:

> A decorator never replaces the primary local identity of the decorated
> target.

For example, `@app.route("/")` is a Flask-owned decorator call, while a later
call to the decorated `index()` function remains `local` and carries `flask`
in `decorated_by` when the evidence can be matched.

`ApiCall.decorated_by` contains only import-backed library names. `local`,
`python`, and `unknown` are filtered. Matching first uses exact file, scope,
and function identity, then a receiver-aware fallback for supported dotted
decorated callables such as `hello.main()`. Full class-aware decorated instance
methods and arbitrary receiver aliases remain unresolved.

## Classification outcomes

Classification uses the resolved source kind and evidence chain:

- direct import aliases produce `DIRECT_IMPORT`;
- project-defined callables produce `LOCAL_DEFINITION`;
- Python builtins and proven builtin shapes produce `BUILTIN`;
- unique local return propagation produces `RETURN_PROPAGATION`;
- re-exports and other resolved chains produce `TRANSITIVE_IMPORT`;
- converged or conflicting source sets produce `FLOW_MERGE`;
- missing terminal evidence produces `UNRESOLVED`.

Parameter evidence participates before final classification. Therefore a call
whose receiver came through a parameter may expose the terminal return,
transitive import, or merge reason rather than `PARAMETER_PROPAGATION`.

## Conservative boundaries

The following conditions prevent a unique primary owner unless independent
evidence resolves them:

- multiple possible local targets or concrete library owners;
- unsupported argument expansion or callback selection;
- unresolved return paths or possible fall-through;
- recursive call, assignment, import, or structured-source cycles;
- dynamic imports, reflection, monkey patching, and runtime attribute hooks;
- arbitrary heap mutation or escaping aliases;
- ambiguous inheritance, metaclass behavior, and external implementations.

At a boundary, PCResolve reports `unknown`, alternatives, and diagnostics as
available. Consumers must not interpret missing evidence as proof that a
runtime owner does not exist.
