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
frontend/ scanner, module mapper and source snapshot
              ↓
facts/ signatures, scopes, imports, calls, returns and effects
              ↓                                  ↓
ownership/collect → ownership/resolve       flow/analyzer.py
              ↓                                  ↓
ownership/types.py and views.py             flow-0.2
                         ↓
                       cli.py
```

The shared layer describes syntax, locations, definitions, bindings, return
dependencies, and supported effects. Ownership and value flow decide how those
facts are interpreted.

## Source navigation

- Module naming and source selection start in `frontend/module_mapper.py`,
  `ModuleMapper.scan_project()`, and `frontend/source_snapshot.py`,
  `module_name_for_path()`.
- Missing assignment or call facts start in `ownership/collect/single_file_assignment.py`
  and `ownership/collect/single_file_call_collection.py`.
- A wrapper's returned ownership starts in
  `ownership/resolve/project_result_binding.py`, `_bind_bounded_local_call_results()`,
  and `ownership/resolve/project_source_tracing.py`.
- Dependencies across `with` exits start in `flow/transfer/summary.py`,
  `_Summary.with_statement()` and `_Summary.execute_context_exit()`.

Implementation modules reside in `frontend/`, `facts/`, `ownership/`, and
`flow/`. The flow proof root is a package boundary; implementations are grouped
by the source construct they model:

| Package | Responsibility |
|---|---|
| `flow/analyzer.py` | Public entry point, configuration and flow analysis orchestration |
| `flow/index/source.py` | Source generation and definition index construction |
| `flow/index/definitions.py` | Class hierarchy, scope and bounded definition facts |
| `flow/analysis/proof_context.py` | Source proof preparation and semantic queries |
| `flow/runtime/analysis_run.py` | Per-run entry traversal and summary merging |
| `flow/transfer/call_entry.py` | Call admission and ordered invocation of transfer phases |
| `flow/transfer/call_expression.py` | Call-resolution, record, binding, effect and result phases |
| `flow/transfer/call_expression_state.py` | Explicit per-call working state shared by those phases |
| `flow/transfer/summary.py` | Query-local summary state and transfer-component composition |
| `flow/transfer/summary_values.py` | Literal, callable and source-class value facts |
| `flow/transfer/summary_class_effects.py` | Class lookup and receiver invalidation effects |
| `flow/transfer/summary_call_evidence.py` | Call evidence, boundaries and argument binding |
| `flow/transfer/summary_expressions.py` | Syntax-specific expression handlers and preflight boundaries |
| `flow/transfer/summary_containers.py` | Container projection, construction and operations |
| `flow/transfer/summary_effects.py` | Function effects and mapping remainder transfer |
| `flow/transfer/summary_context_managers.py` | Context entry/exit and cleanup control flow |
| `flow/transfer/summary_statements.py` | Statement transfer, guards, exception flow and run entry |
| `flow/transfer/environment.py` | Environment merging and source propagation |
| `flow/proofs/classes/` | Class creation, binding, decoration, and class reads |
| `flow/proofs/containers/` | Container predicates, mapping reads, and transfers |
| `flow/proofs/callables/` | Callable construction, binding, retention, and observation |
| `flow/proofs/callables/decorators/` | Decorator effects, imports, exceptions, and text |
| `flow/proofs/callables/dispatch/` | Finite dispatch and call argument validation |
| `flow/proofs/namespaces/` | Function and module namespace proofs |
| `flow/proofs/namespaces/metadata/` | Signature and metadata construction and observation |
| `flow/proofs/namespaces/modules/` | Module attributes, exports, and class effects |
| `flow/proofs/namespaces/source/` | Source binding and source dependency facts |
| `flow/proofs/protocols/` | Context manager, class, import, and stub protocols |

The flow analyzer coordinates proofs through narrow callbacks where needed;
proof modules do not import the analyzer to construct their execution context.
The architecture test checks static imports, supported literal dynamic imports,
unresolved dynamic imports, dependency cycles, and the ownership/flow boundary.
`runtime/limits.py` holds the resource limits shared by both analyzers.
`runtime/_legacy_imports.py` installs a lazy import finder for flat paths from
earlier releases; requesting a legacy path returns the same implementation
module object. Importing `pcresolve` for ownership use does not load value-flow
proofs. Internal code imports implementation paths directly.

## Analysis state

`SourceStore` creates a `SourceSnapshot` containing the exact decoded sources,
ASTs, hashes, module names, and read errors observed by one run.

`frontend/source_syntax.py` supports historical `async` and `await` attribute names for
the value-flow read policy. Token-local normalization retains original names,
source text, byte spans and hashes; unrelated syntax errors remain boundaries.
The ownership read policy keeps its existing parser behavior.

`facts/star_imports.py` supplies source witnesses for wildcard imports whose exporting
modules declare literal `__all__` lists or tuples. It requires unique, stable
source definitions and bounds traversal. Open exports, rebinding, observable
module mutation, import cycles and exhausted budgets supply no resolved alias.
Consumers use these neutral facts without importing the analyzed package.

Ownership wraps that snapshot in three internal types:

| Type | Responsibility |
|---|---|
| `ProjectSnapshot` | Immutable ordered module set and source versions |
| `ProgramIndex` | Per-module analyzers and the project call graph |
| `OwnershipRun` | Diagnostics, symbol tables, classified calls, caches, and recursion guards for one `ProjectAnalyzer.analyze()` invocation |

Repeated ownership runs construct fresh run state. Value flow owns its own
snapshot and caches. There is no public `AnalysisSession`, and the two adapters
must not assume that one invocation shares caches with the other.

The ownership source-fact cache records the declared `SingleFileVisitorFacts`
schema. It does not retain the visitor's whole `__dict__`, query stacks, or
lookup caches. Fact-structure listeners are detached during capture and rebound
to each cloned visitor, so edits to one clone cannot mutate another clone or a
later ownership run. The AST nodes remain tied to the `SourceDocument` version
from which the facts were collected; a changed, removed, or renamed source
requires facts from the corresponding new snapshot.

Value flow separates the analyzer's source index from each recursive summary's
query-local environment and evidence. `_Summary._make_child_summary()` creates
a child with the explicitly supplied result, target, source node, remaining
depth, receiver, and incoming bindings. Context-manager transfer still owns
cleanup through its existing `try/finally` boundary. `_CallExpressionState` is
the internal slotted state shared by the ordered call-transfer phases; it is not a
public result or JSON schema.

The deferred class proof in `flow/proofs/classes/_class_deferred.py` performs a
bounded syntax preflight (2,000 AST nodes) and charges the optional analysis
budget before interpreting declaration-time effects. Each proof attempt owns a
`_DeferredClassProofState`. Its statement interpreter keeps source order,
retains only facts that agree at branch joins, and invalidates stored function
metadata evidence after later writes. Unsupported or open effects return no
proof; the proof does not execute source bodies or widen inference. These
boundaries apply to each proof attempt.

For call transfer, `CallEntryMixin.call_expression()` creates one state for each
admitted call. It passes phase results to subsequent phases and distinguishes
an unresolved `None` from an empty result. The summary owns call records and
evidence; transfer phases update the environment for that invocation.

Ownership publishes its next source-fact cache only after project analysis
finishes. Failed captures or budget exits retain the previous cache, whose
entries remain subject to source and module-context checks. Flow rebuilds
query state at analysis entry. The kind-alias proof stages decorator evidence
locally and publishes it only after all alias checks succeed.

Constructor binding consumes retained-store witnesses; fresh-receiver analysis
requests an effects summary. An empty witness list contains no established
stores; an effects result of `None` leaves the effects unproved. Neither value
proves that execution occurred. These distinctions and cache lifetimes should be
preserved when modifying proof producers or their consumers.

## Shared fact layer

| Module | Final responsibility |
|---|---|
| `frontend/source_snapshot.py` | Immutable source documents, hashes, ASTs, module index, and snapshot validation |
| `facts/program_facts.py` | Source spans, function signatures, AST call binding, and opaque parameter-source projection |
| `facts/call_resolution.py` | Definition candidates and parent-linked call contexts |
| `facts/scope_facts.py` | Immutable loaded, bound, global, nonlocal, and capture-name facts |
| `facts/import_facts.py` | Import aliases and relative-import resolution |
| `facts/return_resolution.py` | Bounded substitution and composition of return dependencies |
| `facts/effect_facts.py` | Proven builtin container protocols and complete straight-line function effects |

Shared facts follow these invariants:

- they use only the Python standard library;
- they do not import ownership adapters, value-flow policy, classification, or
  public result types;
- source payloads are opaque where ownership and value flow need different
  representations;
- uncertain expansions and unsupported constructs remain explicit;
- source positions and collection order are deterministic;
- statically declared internal package imports are acyclic.

`tests/test_shared_layer_boundaries.py` protects the shared-layer dependency
direction and the complete statically recoverable import graph. It detects
package-relative dynamic imports, unresolved dynamic imports, cycles, and
reverse dependencies on the legacy compatibility layer. The current internal
graph is acyclic under this checker.
The check recognizes `importlib.import_module` (including direct import aliases)
and `__import__` with literal names or `__package__` plus a literal suffix.
Other recognized calls are rejected as unresolved, except for the legacy
compatibility registry, whose explicit mapping is enumerated as dependencies.
It does not perform general data-flow analysis of reassigned import functions
or computed import names.

## Ownership adapter

### Single-file collection

`SingleFileAnalyzer` remains the public AST visitor facade. It owns visitor
state, lexical scope primitives, import collection, and the `analyze_source()`
entry point. Cohesive policies are implemented by mixins on the same visitor,
so AST order and binding time remain explicit and unchanged.

| Module | Responsibility |
|---|---|
| `ownership/collect/single_file_definitions.py` | Function, lambda, class, decorator, inheritance, and constructor facts |
| `ownership/collect/single_file_assignment.py` | Assignment visitors, container metadata, and right-hand-side staging |
| `ownership/collect/single_file_binding_resolution.py` | Target, iterator, decorator, and finite guard bindings |
| `ownership/collect/single_file_control_flow.py` | Branch joins, loops, comprehensions, generators, and scope declarations |
| `ownership/collect/single_file_returns.py` | Return provenance, tuple-aware summaries, and protocol return values |
| `ownership/collect/single_file_container_shapes.py` | Builtin container and item-shape facts |
| `ownership/collect/single_file_source_resolution.py` | Expression-to-source dispatch |
| `ownership/collect/single_file_parameter_dependency.py` | Parameter-derived expression evidence |
| `ownership/collect/single_file_receiver_resolution.py` | Callable, receiver, operator, conversion, and bounded result-owner resolution |
| `ownership/collect/single_file_method_resolution.py` | Method receiver/source collection |
| `ownership/collect/single_file_call_collection.py` | Call-edge snapshots, API-call visitors, and ordered call records |
| `ownership/collect/single_file_argparse.py` | Conservative argparse Namespace field shapes |
| `ownership/collect/single_file_builtins.py` | Shared unshadowed-builtin predicate |

All mixins operate on `SingleFileAnalyzer` state. They are internal
organization boundaries, not independent analyzer instances.

### Project resolution

`ProjectAnalyzer` is the project-level facade. It scans and snapshots the
selected sources, runs one single-file analyzer per module, builds the project
index, performs bounded cross-file propagation, classifies calls, and assembles
`ProjectAnalysis`.

| Module | Responsibility |
|---|---|
| `ownership/resolve/project_call_context.py` | Exact local targets, call contexts, argument binding, and parameter substitution |
| `ownership/resolve/project_result_binding.py` | Assigned results, callbacks, iterators, and proven method-result rewrites |
| `ownership/resolve/project_source_tracing.py` | Cross-module source chains, return summaries, wildcard fallback, and final source lookup |
| `ownership/resolve/project_method_ownership.py` | Structured receivers, inherited methods, parameter/container propagation, and instance fields |
| `ownership/resolve/project_local_classes.py` | Local class identities, inheritance, constructor fields, and callable-instance evidence |
| `ownership/resolve/project_call_classification.py` | Call-record assembly, owner convergence, reasons, confidence, alternatives, and resolved names |
| `ownership/resolve/call_result_resolution.py` | Bounded `CallResult` state resolution |
| `ownership/resolve/instance_method_resolution.py` | `InstanceMethod` receiver resolution |
| `ownership/resolve/container_resolution.py` | Item, iteration, returned-element, and Python-shape resolution |

Ownership policy is kept separate from traversal:

| Module | Responsibility |
|---|---|
| `ownership/builtin_ownership.py` | Proven builtin receiver and result-shape rules |
| `ownership/ownership_contracts.py` | Verified import-backed result and callback contracts |
| `ownership/source_resolution.py` | `SourceSet` primary convergence |
| `ownership/classification.py` | Final ownership reason, confidence, and alternatives |
| `ownership/decorator_provenance.py` | Decorator evidence lookup |
| `ownership/library_usage.py` | Per-library aggregation |

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

Call-edge target matching holds a run-local cycle guard before inspecting
receiver provenance: parameter and return lookup may re-enter target matching
before a call context exists. Target matching, origin candidates, receiver
method candidates, and returned Python shapes also share a proof budget of
4096 query entries and 32 nested queries. This bounds cross-resolver expansion
as well as direct cycles. A cutoff invalidates the enclosing proof, preserving
`unknown` ownership or an unresolved shape rather than converging from a
truncated candidate set. Each independent query starts a fresh budget, and each
analysis run replaces the guard and budget state. These are internal ownership
limits; they do not change the stable JSON schema or the value-flow budgets.

Single-file method and container-shape queries reuse expression results within
one uninterrupted lexical query. Their shared cache keys include the query,
AST expression, and lexical scope; reentrant queries retain a conservative
unknown result. The cache is discarded when the outer query finishes, including
on exceptions, so later assignments, branch joins, and scope changes observe
fresh facts. This avoids repeated expansion of unresolved method chains without
persisting ownership evidence across visitor state changes.

Project dispatch indexes retain definition and call-site collection order and
only exclude names that the existing target matcher cannot accept. Constructors,
explicit callable alternatives, nested functions, callable instances, and
inherited dispatch still use the same target proofs. Reverse call lookup is
also used when reading an element of `*args` or `**kwargs` and when finding
runtime subclasses that reach an inherited field read. These queries retain
mapping and callable-instance candidates and still check each selected target.
Exact source-position lookup shares the edge index; callable-source rewrites
update only the affected name buckets. Target-resolution results are not cached
across those rewrites. Unrelated negative target checks no longer consume nested
proof entries, so some previously budget-limited unknown results can retain
additional evidence without raising either proof limit.

Parameter provenance uses a reverse signature index, preserving definition
order and the first position of each parameter name. Definition collection
invalidates this index; call-site evidence is read afresh. Callable-instance
dispatch reuses static class candidates and incoming-edge buckets. Sources that
require recursive parameter proofs and classes with inherited dispatch retain
all `__call__` candidates. Exact target checks remain query-local; edge and
module-binding rewrites invalidate the callable indexes.

Repeated `FlowAnalyzer.analyze()` calls reuse the latest source definition,
import, and module indexes when all source documents, the source set, and ordered
import roots are unchanged. Each call still rereads source contents, including
files with unchanged size and mtime. Changed, added, removed, or unreadable files
invalidate the generation. Query summaries, contexts, budget counters, effect
facts, and returned-object facts reset for every analysis, including cache hits.
This reuse is local to one analyzer and adds no public session or output fields.

When one Flow source changes, definition collection, imports and binding syntax
facts are rebuilt only for changed files. Unchanged files retain facts keyed by
the exact source document, module identity, reading policy and ordered import
roots. Aggregate name indexes are rebuilt in the original file order; semantic
summaries and budgets still reset. Failed and removed files drop their facts.

Ownership method-result candidates and import-source prefixes use versioned
fact indexes. Collection changes notify dependent indexes; existing edge/source
rewrite routines invalidate callable evidence. Cache hits do not scan every
module to establish a generation. AST calls, assignments, classes and parent
relationships are indexed lazily within the run. Completed constructor-field
readonly proofs can be reused under the same field and recursive context;
failed or cyclic proofs are not retained. Return dependencies use reverse
dependencies to schedule changed summaries, preserving synchronous rounds,
original path ordering, iteration counts and limits.

`ProjectAnalyzer(root, reuse_source_facts=True)` optionally retains a
`SingleFileFacts` record captured before project propagation, not a visitor
instance. Repeated calls create a fresh visitor, restore source-derived facts
for unchanged documents, share only the read-only AST, and rebind callbacks to
the new visitor. File edits, additions, deletions and parse failures update the
cache. Every run still performs cross-file propagation, classification and
provenance construction. This mode increases memory and first-run copying cost
and is disabled by default; it is not persistent storage or an incremental
cache of semantic answers.

`AnalysisLimits` provides optional time, work and resident-memory checks for one
`analyze()` call. Ownership and Flow maintain separate resource counters. A
limit raises `AnalysisLimitExceeded`; the CLI exits with an error and does not
emit a partial result as complete. Defaults are unrestricted and do not change
the ownership proof budget or Flow boundaries. Checks are cooperative at files,
syntax visits, records and resolver entries, not OS-enforced hard limits:
individual parsing/copying operations can finish before the next check. Memory
uses current RSS on Windows/Linux and peak RSS on the resource fallback.
Output serialization and later queries on a returned result are outside these
analysis limits.

`scripts/perf_scalability.py` runs each sample in a fresh process, measures
synthetic projects at multiple sizes, unchanged queries and single-file edits,
including cold ownership with and without the optional fact cache. It checks
reused results against complete fresh outputs and records wall/CPU time,
post-analysis RSS, process peak RSS, raw per-process samples and implementation
identity. Five independent processes are the default. These generated workloads
supplement real-project measurements rather than establishing a universal
complexity bound.

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
