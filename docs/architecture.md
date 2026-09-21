# PCResolve Architecture

PCResolve has two analysis surfaces:

- stable call-site ownership, with symbol provenance as its explanation layer;
- experimental value flow, exposed through the separate `flow-0.2` contract.

Both analyses consume shared, policy-neutral source facts. They keep separate
state, propagation rules, boundaries, and public outputs.

## System boundary

PCResolve parses project source without importing or executing it. For each
call expression, ownership reports one primary owner:

- an import-backed top-level library name;
- `python` for Python-provided APIs and proven builtin value shapes;
- `local` for project-defined callables;
- `unknown` when the available evidence is insufficient.

The core contract does not distinguish standard-library modules from PyPI
packages. Both are import-backed libraries and retain their top-level import
name. PCResolve is not a complete type system, language server, runtime
inspector, call graph, security scanner, or license scanner.

## Pipeline

```text
scanner.py / module_mapper.py
              ↓
source_snapshot.py
              ↓
shared facts
  program_facts.py       call_resolution.py       scope_facts.py
  import_facts.py        return_resolution.py     effect_facts.py
              ↓                                  ↓
ownership adapter                           value-flow adapter
single_file.py → cross_file.py              flow.py
              ↓                                  ↓
types.py / views.py / cli.py                flow-0.2 / cli.py
```

The shared layer describes syntax, locations, definitions, bindings, return
dependencies, and supported effects. Ownership and value flow decide how those
facts are interpreted.

## Analysis state

`SourceStore` creates a `SourceSnapshot` containing the exact decoded sources,
ASTs, hashes, module names, and read errors observed by one run.

Ownership wraps that snapshot in three internal types:

| Type | Responsibility |
|---|---|
| `ProjectSnapshot` | Immutable ordered module set and source versions |
| `ProgramIndex` | Per-module analyzers and the project call graph |
| `OwnershipRun` | Diagnostics, symbol tables, classified calls, caches, and recursion guards for one `ProjectAnalyzer.analyze()` invocation |

Repeated ownership runs construct fresh run state. Value flow owns its own
snapshot and caches. There is no public `AnalysisSession`, and the two adapters
must not assume that one invocation shares caches with the other.

## Shared fact layer

| Module | Final responsibility |
|---|---|
| `source_snapshot.py` | Immutable source documents, hashes, ASTs, module index, and snapshot validation |
| `program_facts.py` | Source spans, function signatures, AST call binding, and opaque parameter-source projection |
| `call_resolution.py` | Definition candidates and parent-linked call contexts |
| `scope_facts.py` | Immutable loaded, bound, global, nonlocal, and capture-name facts |
| `import_facts.py` | Import aliases and relative-import resolution |
| `return_resolution.py` | Bounded substitution and composition of return dependencies |
| `effect_facts.py` | Proven builtin container protocols and complete straight-line function effects |

Shared facts follow these invariants:

- they use only the Python standard library;
- they do not import ownership adapters, value-flow policy, classification, or
  public result types;
- source payloads are opaque where ownership and value flow need different
  representations;
- uncertain expansions and unsupported constructs remain explicit;
- source positions and collection order are deterministic;
- internal package imports are acyclic.

`tests/test_shared_layer_boundaries.py` protects the dependency direction and
the package-wide no-cycle invariant.

## Ownership adapter

### Single-file collection

`SingleFileAnalyzer` remains the public AST visitor facade. It owns visitor
state, lexical scope primitives, import collection, and the `analyze_source()`
entry point. Cohesive policies are implemented by mixins on the same visitor,
so AST order and binding time remain explicit and unchanged.

| Module | Responsibility |
|---|---|
| `single_file_definitions.py` | Function, lambda, class, decorator, inheritance, and constructor facts |
| `single_file_assignment.py` | Assignment visitors, container metadata, and right-hand-side staging |
| `single_file_binding_resolution.py` | Target, iterator, decorator, and finite guard bindings |
| `single_file_control_flow.py` | Branch joins, loops, comprehensions, generators, and scope declarations |
| `single_file_returns.py` | Return provenance, tuple-aware summaries, and protocol return values |
| `single_file_container_shapes.py` | Builtin container and item-shape facts |
| `single_file_source_resolution.py` | Expression-to-source dispatch |
| `single_file_parameter_dependency.py` | Parameter-derived expression evidence |
| `single_file_receiver_resolution.py` | Callable, receiver, operator, conversion, and bounded result-owner resolution |
| `single_file_method_resolution.py` | Method receiver/source collection |
| `single_file_call_collection.py` | Call-edge snapshots, API-call visitors, and ordered call records |
| `single_file_argparse.py` | Conservative argparse Namespace field shapes |
| `single_file_builtins.py` | Shared unshadowed-builtin predicate |

All mixins operate on `SingleFileAnalyzer` state. They are internal
organization boundaries, not independent analyzer instances.

### Project resolution

`ProjectAnalyzer` is the project-level facade. It scans and snapshots the
selected sources, runs one single-file analyzer per module, builds the project
index, performs bounded cross-file propagation, classifies calls, and assembles
`ProjectAnalysis`.

| Module | Responsibility |
|---|---|
| `project_call_context.py` | Exact local targets, call contexts, argument binding, and parameter substitution |
| `project_result_binding.py` | Assigned results, callbacks, iterators, and proven method-result rewrites |
| `project_source_tracing.py` | Cross-module source chains, return summaries, wildcard fallback, and final source lookup |
| `project_method_ownership.py` | Structured receivers, inherited methods, parameter/container propagation, and instance fields |
| `project_local_classes.py` | Local class identities, inheritance, constructor fields, and callable-instance evidence |
| `project_call_classification.py` | Call-record assembly, owner convergence, reasons, confidence, alternatives, and resolved names |
| `call_result_resolution.py` | Bounded `CallResult` state resolution |
| `instance_method_resolution.py` | `InstanceMethod` receiver resolution |
| `container_resolution.py` | Item, iteration, returned-element, and Python-shape resolution |

Ownership policy is kept separate from traversal:

| Module | Responsibility |
|---|---|
| `builtin_ownership.py` | Proven builtin receiver and result-shape rules |
| `ownership_contracts.py` | Verified import-backed result and callback contracts |
| `source_resolution.py` | `SourceSet` primary convergence |
| `classification.py` | Final ownership reason, confidence, and alternatives |
| `decorator_provenance.py` | Decorator evidence lookup |
| `library_usage.py` | Per-library aggregation |

### Ownership sequence

1. Discover `.py` and `.pyi` files and map paths to module names.
2. Freeze one source snapshot.
3. Parse each module and collect lexical bindings, definitions, calls, returns,
   receiver facts, and structured source evidence.
4. Build the project call graph and definition indexes.
5. Apply bounded call-context, result, container, and instance propagation.
6. Trace each call's source chain and classify its primary owner.
7. Build `ApiCall`, `SymbolProvenance`, `LibraryUsage`, diagnostics, and views.

## Value-flow adapter

`FlowAnalyzer` uses shared source, signature, binding, definition, scope,
return, import, and effect facts. It keeps its own dependency graph and emits
only the experimental `flow-0.2` model.

Value flow records:

- call targets and actual-to-formal bindings;
- parameter and implicit receiver dependencies;
- call-result and entry-return dependencies;
- supported container mutations and effects;
- boundary reasons for missing definitions, ambiguity, unsupported syntax,
  recursion, and budget cutoffs.

It does not alter ownership classification or the ownership `schema_version`.
An empty path list is not a no-flow proof while boundaries remain.

## Core internal data

| Type | Meaning |
|---|---|
| `SourceSpan` | Complete source range and snapshot-local call identity |
| `FunctionSignature` | Python parameter kinds, variadics, and declaration-time defaults |
| `CallSite` | Single-file call expression, source range, scope, and base source |
| `SymbolRef` | Single-file symbol provenance fact |
| `FunctionId` | Project-local module and qualified function identity |
| `CallEdge` | Caller, callee, receiver, arguments, assignment, and call position |
| `SourceSet` | Ordered alternative source evidence with convergence origin |
| `ApiCall` | Stable ownership classification for one call expression |
| `SymbolProvenance` | Stable explanation record for one symbol source |

Structured source variants and their convergence rules are documented in
[Source Semantics](source-semantics.md). The trace/classification boundary is
documented in [Trace Contract](trace-contract.md).

## Dependency and behavior invariants

- Stable ownership and experimental value flow have separate public schemas.
- Shared fact types never become public output implicitly.
- Analysis never imports or executes the analyzed project.
- Ownership is evidence-backed; names, project names, and arbitrary library
  allowlists do not establish an owner.
- Recursion guards bound import cycles, assignment cycles, recursive calls,
  structured sources, and return expansion.
- Ambiguous concrete owners remain alternatives with an `unknown` primary
  unless a documented convergence rule applies.
- Output ordering is deterministic and source locations retain complete start
  and end coordinates where available.
- The runtime package has no third-party dependency and supports Python 3.9+.

## Resolution boundaries

Ownership remains conservative for unresolved dynamic imports, reflection,
monkey patching, arbitrary descriptors, runtime-only dispatch, ambiguous
multiple inheritance, and external implementations without source evidence.

Value flow is additionally bounded by the selected source set, call depth,
function budget, call-context budget, supported control flow, and modeled
effects. Boundaries are part of the result and must be inspected by consumers.

## Verification

Architecture changes must preserve complete ownership and flow fingerprints,
pass the focused tests, and pass the appropriate release gates:

```bash
python -m pytest -q
python scripts/evaluate_ground_truth.py --view all
python scripts/evaluate_value_flow_matrix.py --strict
```

Current evaluation scope and results are summarized in
[Validation](validation.md).
