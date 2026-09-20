# PCResolve Architecture

PCResolve's primary analysis surface is call-site ownership, supported by symbol
provenance. `all_api_calls` is the primary classification output.
`all_symbol_provenance` explains the symbol flows that support those call
classifications. The experimental `FlowAnalyzer` separately exposes parameter,
return, and effect evidence for downstream analyses.

## Ownership module refactor (in progress)

The stable ownership pipeline and the experimental value-flow adapter retain
their separate state, policies, and public outputs. This refactor changes code
organization only: `SingleFileAnalyzer` remains the AST visitor,
`ProjectAnalyzer` remains the project orchestration entry point, and the
documented constructors, `analyze_source()`, `analyze_project()`, JSON schemas,
call inventory, evidence ordering, and conservative boundaries stay unchanged.

The first extraction moves evidence-backed result contracts to
`ownership_contracts.py` and proven builtin receiver rules to
`builtin_ownership.py`. Both are ownership-only policy modules; neither belongs
in the neutral program-fact layer or depends on an analyzer. The project
analyzer still composes the single-file analyzer, but it now imports these
shared ownership policies directly rather than through private names in
`single_file.py`. Subsequent extractions move the `CallResult` ownership state
machine to `call_result_resolution.py` and instance receiver resolution to
`instance_method_resolution.py`. Container item, iteration, returned-element,
and Python-shape resolution live together in `container_resolution.py`;
`ProjectAnalyzer` supplies project indexes, recursive resolver operations, and
import-origin evidence through internal mixin boundaries.
On the single-file side, receiver and method-source collection is isolated in
`single_file_method_resolution.py`; it operates on the visitor's lexical state
without introducing a second analyzer state or changing AST visit order.
Call-edge snapshots and public per-file call records are isolated in
`single_file_call_collection.py`, while retaining the same visitor-owned
binding maps, position identity, and append order.
Ordinary assignment handling and its flow-sensitive container metadata are
isolated in `single_file_assignment.py`; target binding still occurs on the
same visitor instance and at the same point in traversal.
Expression-to-source tracing is isolated in
`single_file_source_resolution.py`. Its public visitor hook now dispatches to
bounded handlers for method calls, chained calls, ordinary call results,
subscripts, lambdas, and literal containers; the former monolithic
`trace_source()` decision tree is no longer one indivisible method.
Loop-carried shapes, iterator binding, generator yields, branch joins,
comprehensions, and scope declarations are grouped in
`single_file_control_flow.py`. Iterator-yield resolution is further divided
into non-call tuple evidence, fixed `os.walk` contracts, explicit iterator
contracts, and builtin `enumerate`/`zip` behavior.
Function, lambda, class, decorator, and constructor-field collection is
isolated in `single_file_definitions.py`. `FunctionDefinitionFacts` freezes
receiver, parameter-kind, default-value, and variadic facts before the visitor
enters the function scope; body traversal and summary construction are now
separate stages instead of one 162-line handler.
Container and Python value-shape facts are grouped in
`single_file_container_shapes.py`. Expression-shape dispatch is separated from
attribute, subscript, binary, and call-result handlers; list-append processing
now has distinct owner, tuple-field, item-kind, and literal-field joins.
Project orchestration now creates one explicit internal run in
`ownership_model.py`: an immutable `ProjectSnapshot` fixes the ordered modules
and source versions, `ProgramIndex` owns the per-module analyzers and project
call graph, and `OwnershipRun` owns diagnostics for that invocation. Existing
`_source_snapshot` and `project_cg` attributes remain compatibility aliases
while resolver methods are migrated incrementally. Project symbol tables,
classified call records, recursion guards, and the constructor-field cache are
also run-owned, so repeated use of one analyzer cannot reuse stale resolution
state. These types are internal; they do not add a public session or change
either output schema.
Project-level result rewriting is isolated in `project_result_binding.py`.
It owns bounded local-call results, callback-map results, generator iteration
substitution, and proven receiver-method results. Assigned-result propagation
is split into target selection, positional result selection, record rewriting,
and future-edge rewriting rather than one pass with interleaved concerns.
Exact project call targets and parameter substitution are isolated in
`project_call_context.py`. It owns definition lookup, bounded parent-linked
contexts, positional and variadic argument binding, supported callback
contracts, and local method dispatch. Aggregate source evaluation, incoming
argument collection, and edge-target matching are each staged into small
handlers while continuing to use the analyzer's project graph and conservative
ownership policies.
Final cross-file source-chain traversal is isolated in
`project_source_tracing.py`. It resolves receiver factories, return summaries,
class attributes, call-site parameter substitutions, wildcard fallbacks, and
the final top-level source. Its recursive trace entry now delegates unresolved,
parameter, structured, and ordinary sources to separate handlers while sharing
the analyzer's explicit cycle guard.
Method-receiver ownership and structured cross-file resolution are isolated in
`project_method_ownership.py`. It owns inherited method lookup, parameter and
container receiver propagation, expression-method convergence, and runtime
instance-field resolution. The former 279-line argument-method resolver now
dispatches by structured source kind, with separate bounded-call, iteration,
item, variadic-pack, derived-expression, and terminal-parameter stages.
Local class identity and callable-instance evidence are isolated in
`project_local_classes.py`. It owns inheritance traversal, constructor and
factory result identities, field bindings, callable-parameter escape checks,
and receiver-class filtering for project edges. These queries consume the
shared project graph without becoming a second class index or mutable state
owner.

Further extraction is staged rather than an all-at-once class move:

1. Split large visitor and structured-source methods into smaller handlers
   while preserving AST visitation order, call-position identity, mutable
   binding timing, candidate priority, and recursion guards.
2. Move coherent file-level shape, call-site, and definition collection and
   project-level result-binding passes behind explicit internal interfaces.
3. Migrate project orchestration state from analyzer compatibility attributes
   to `OwnershipRun` consumers without creating a second source of truth.
4. Untangle the mutually recursive project resolution methods before moving
   them into a dedicated resolver. A resolver may retain semantic recursion,
   but modules must not form Python import cycles or gain hidden global state.

No public `AnalysisSession` or generic ownership/flow propagation engine is
implied by this refactor.

For each behavior-preserving slice, compare complete public-output fingerprints
on the 42-project ownership corpus and the value-flow matrix with
`scripts/compare_analysis_baseline.py`, then run the focused tests, live
ground-truth gate, strict value-flow matrix, and full test suite. A changed
fingerprint is investigated rather than accepted by refreshing golden data.

## Pipeline Overview

```
scanner.py  →  module_mapper.py  →  single_file.py  →  cross_file.py  →  cli.py  →  views.py
                                        ↑                    ↑
                                   symbol_table.py    source_resolution.py
                                   scope.py           classification.py
                                   sources.py         library_usage.py
                                   ir.py              decorator_provenance.py
                                   types.py           call_graph.py
                                   builtin_ownership.py
                                   ownership_contracts.py
                                   single_file_method_resolution.py
                                   single_file_call_collection.py
                                   single_file_assignment.py
                                   single_file_source_resolution.py
                                   single_file_control_flow.py
                                   single_file_definitions.py
                                   single_file_container_shapes.py
                                                      ownership_model.py
                                                      project_call_context.py
                                                      project_result_binding.py
                                                      project_source_tracing.py
                                                      project_method_ownership.py
                                                      project_local_classes.py
                                                      call_result_resolution.py
                                                      instance_method_resolution.py
                                                      container_resolution.py
                                                      call_resolution.py
                                                      scope_facts.py
                                                      return_resolution.py
                                                      effect_facts.py
                                                      import_facts.py
                                   diagnostics.py
```

## Layer Summary

| Layer | Module | Input | Output |
|-------|--------|-------|--------|
| Scan | `scanner.py` | Project root path | List of `.py`/`.pyi` files (excluding venv) |
| Module map | `module_mapper.py` | Project directory or explicit source file | File path ↔ dotted module name |
| Parse + single-file | `single_file.py` | Source code | `SymbolTable`, api_calls (dict list), `call_site_objects`, `symbol_refs` |
| Single-file method sources | `single_file_method_resolution.py` | Method-call AST and lexical visitor state | Structured receiver/method source evidence |
| Single-file call collection | `single_file_call_collection.py` | Call AST, lexical bindings, receiver evidence | Ordered API-call records and internal `CallEdge` facts |
| Single-file assignments | `single_file_assignment.py` | Assignment AST, lexical scope, container metadata | Flow-sensitive bindings and structured assignment sources |
| Single-file source resolution | `single_file_source_resolution.py` | Expression AST and visitor-owned lexical facts | Structured expression source and call-result evidence |
| Single-file control flow | `single_file_control_flow.py` | Loop, branch, generator, and comprehension AST | Flow-sensitive bindings, branch joins, and iteration facts |
| Single-file definitions | `single_file_definitions.py` | Definition AST and enclosing lexical state | Function/class summaries, parameter bindings, decorator and constructor facts |
| Single-file container shapes | `single_file_container_shapes.py` | Container expressions, lexical bindings, and append calls | Python shapes, homogeneous item/tuple facts, and field-shape joins |
| Cross-file | `cross_file.py` | Per-file tracers | `ProjectAnalysis` (global symbols, chains, api calls, provenance, library usage) |
| Ownership run state | `ownership_model.py` | Ordered modules and one `SourceSnapshot` | Internal `ProjectSnapshot`, `ProgramIndex`, and `OwnershipRun` |
| Project call context | `project_call_context.py` | Project call graph, definition index, call positions, and structured arguments | Exact local targets, bounded contexts, and conservative parameter substitutions |
| Project result binding | `project_result_binding.py` | Project call graph, function summaries, and per-file call records | Bounded assigned-result, callback, iterator, and method-result rewrites |
| Project source tracing | `project_source_tracing.py` | Module map, per-file symbols, return summaries, and recursion guard | Ordered source chains and conservative final top-level sources |
| Project method ownership | `project_method_ownership.py` | Structured receivers, project call graph, parameter bindings, and local class evidence | Conservative method-owner candidates and structured source resolutions |
| Project local classes | `project_local_classes.py` | Local class summaries, inheritance facts, constructor sources, and call edges | Bounded class identities, field bindings, and callable-instance candidates |
| Call-result ownership | `call_result_resolution.py` | `CallResult`, project indexes, recursion guard | Resolved display, module, and conservative owner tuple |
| Instance-method ownership | `instance_method_resolution.py` | `InstanceMethod`, receiver evidence, project indexes | Resolved display, module, and conservative owner tuple |
| Container ownership | `container_resolution.py` | Item/iteration sources, returned-element facts, Python shapes | Conservative item and iterable owner candidates |
| Ownership policy | `builtin_ownership.py`, `ownership_contracts.py` | Proven builtin shapes and verified import-backed result contracts | Conservative owner/shape rule lookups used by both ownership phases |
| Shared syntax and binding | `program_facts.py` | AST positions, signatures, opaque argument payloads | Source spans and pure binding projections |
| Shared source versions | `source_snapshot.py` | Explicit file set and read/naming policies | Source snapshots, cached ASTs, read-only module index |
| Shared definition lookup | `call_resolution.py` | Adapter-collected definitions and call occurrences | Ordered candidate index and parent-linked call contexts |
| Shared lexical facts | `scope_facts.py` | Function/lambda AST or one statement body | Immutable loaded, bound, global, and nonlocal name sets |
| Shared return substitution | `return_resolution.py` | Normalized call bindings and adapter-owned dependency records | Bounded, composed return dependencies |
| Shared effect facts | `effect_facts.py` | Proven builtin container shapes or one function AST | Immutable protocol and complete straight-line effect descriptions |
| Shared import facts | `import_facts.py` | One import AST node and lexical module context | Immutable alias records and resolved relative module names |
| Value flow | `flow.py` | Source files/import roots, entry selector, budgets | Experimental `FlowAnalysis` |
| Views | `views.py` | `ProjectAnalysis` | Dict/list for JSON serialization |
| CLI | `cli.py` | Project root + args | Human-readable text or JSON |

## Shared program facts: first migration

`program_facts.py` is an internal layer consumed by both ownership and value
flow. It uses only the standard library and has no dependency on either
analyzer, classification rules, or public result types.

| Component | Fact or operation | Consumers |
|-----------|-------------------|-----------|
| `SourceSpan` | File and complete start/end coordinates; snapshot-local call identity | Ownership `CallSite` / `CallEdge`, flow call IDs |
| `FunctionSignature` | Positional-only, positional-or-keyword, keyword-only, variadic names, and declaration-time defaults | Ownership `FunctionSummary.signature`, flow syntax binding |
| `bind_ast_call()` | Explicit and literal-expanded argument bindings with ordered uncertainty reasons | Flow's AST adapter |
| `bind_parameter_sources()` | Parameter projections over opaque source payloads | Ownership's bounded contexts and incoming-edge propagation |
| `starred_item_source()` | Item projection when a single known-start expansion can supply a position | Ownership's parameter and pack adapters |

These operations do not resolve callees, trace default expressions, classify
libraries, or compute return summaries. Adapters choose source payloads and
receiver binding, and attach analysis-specific evidence and boundaries.
`SourceSpan.key` preserves existing `flow-0.2` IDs; it is not a persistent
identity across edits or different source snapshots. The path representation is
chosen by the existing analysis session, not normalized by this helper.

This migration preserves existing policy differences:

- Flow uses Python parameter kinds for keyword binding and reports uncertain
  dynamic expansions. Ownership preserves its existing explicit-keyword
  priority, including legacy summaries without complete kind metadata.
- An ownership bounded context projects a single parameter source; a variadic
  pack requires selecting a later item. Incoming-edge propagation can collect
  pack sources. These are `CONTEXT_BINDING` and `OWNERSHIP_BINDING` policies.
- Multiple unresolved keyword expansions currently block default substitution
  in bounded contexts; incoming-edge propagation retains its existing default
  fallback. This is characterized by tests, not silently corrected during the
  extraction.
- Ownership's empty `positional_params` compatibility fallback remains intact.
  Flow's default-evidence assembly remains in its adapter. Duplicate and missing
  argument validation is not expanded by this refactor.

Public entry points and ownership / `flow-0.2` schemas are unchanged. Ownership
does not invoke `FlowAnalyzer`. Import syntax, target candidates, lexical facts,
return substitution, captures, and effects have been migrated independently;
the following sections describe the completed stages.

## Shared source snapshots and module index: second migration

`source_snapshot.py` supplies source versions and module naming to both
analyzers. `ProjectAnalyzer` and `FlowAnalyzer` each own a `SourceStore` for their
session. The layer has no dependency on analysis summaries or classification.
A future shared analysis session is an optional composition and performance
feature rather than part of this facts-layer migration. Sharing the current
store alone would reuse some ASTs, but would still rescan and reread files and
would not guarantee that both analyzers observed one point-in-time source
generation. No public constructor option or output field is introduced here.

| Component | Responsibility |
|-----------|----------------|
| `SourceDocument` | Decoded text, SHA-256 of that text, AST, or native read/parse error |
| `SourceSnapshot` | Ordered requested file set and immutable document lookup |
| `SourceStore` | Reread actual content; reuse unchanged decoded ASTs; retain only the latest requested version per file |
| `ModuleIndex` | Preserve ordered file-to-module candidates, package facts, and existing last-file lookup behavior |
| `module_name_for_path()` | Derive names under the existing adapter's compatibility policy |

Every snapshot reads each requested file's content rather than trusting its size
or modification time. ASTs can be reused across decode policies when the decoded
text matches. Changed, unreadable, or removed sources cannot supply stale trees.
Earlier snapshots keep their own document versions. Document and lookup records
are immutable; AST nodes are read-only by convention, and visitors must never
modify them. Source hashes retain the existing meaning: decoded UTF-8 text after
text-mode newline normalization, rather than original file bytes.

Source failures remain data at this layer. Ownership translates them into its
existing encoding/read/syntax diagnostics; flow translates them into
`source_unavailable` boundaries. Flow continues to include hashes only for
successfully parsed sources in its public snapshot. Old expansion results still
require reanalysis after source changes under the existing hash/source-set guard.

Compatibility choices remain explicit and tested:

- Ownership uses `utf-8`; flow uses `utf-8-sig`. A BOM still produces an
  ownership syntax diagnostic and is accepted by flow.
- Ownership omits a root `__init__.py` module. Flow retains the existing
  `__init__` name, and nested package initializers map to the package name.
- Ownership retains legacy suffix replacement, including `pkg.contractsi` for
  `pkg/contracts.pyi`. Flow uses extension splitting and retains both `.py` and
  `.pyi` candidates under `pkg.contracts`. Correcting ownership stub naming is
  a separate behavior change, not part of this extraction.
- Flow retains ordered import-root selection and file-directory fallback.
  Import roots never discover or authorize additional source files.
- The CLI normalizes a positional flow source file or a file path read from
  stdin to FlowAnalyzer's existing single-item `source_files` input. This is
  the same source-selection path as `--source-file`; it does not change the
  analyzer API, module policy, source snapshot, or `flow-0.2` schema.
- `ModuleMapper` preserves its mutable compatibility lookups and scan order.
  Its private index describes the current scan; existing cumulative lookup
  behavior across rescans remains compatibility behavior and must not be
  silently changed by a future session API.

Module naming is shared; import interpretation and definition collection remain
in their adapters. The index does not choose a unique callee from duplicate
module candidates or expose the private ownership call graph.

## Shared target candidates and call contexts: third migration

`call_resolution.py` indexes definitions collected by each analyzer without
assigning ownership, type, or dispatch meaning. `DefinitionRecord` stores the
adapter's module name, lexical qualified name, kind, source location, and an
opaque payload. `DefinitionIndex` preserves collection order and duplicate
definitions. Exact, fully qualified, and nearest lexical lookups return all
candidates unless the existing flow name policy requires one unique result.

The ownership adapter indexes its `FunctionSummary` and `ClassSummary` values.
The value-flow adapter indexes `(FunctionRef, AST)` pairs. Consequently, both
use the same candidate operations while retaining different collection rules:
ownership's call graph keeps one summary for each logical dictionary key;
value flow retains repeated definitions at separate source locations. The
shared index never resolves receiver types, applies inheritance, classifies a
library, evaluates decorators, or interprets callable source sets. Those remain
adapter policies.

`CallContext` stores one selected target, its exact call occurrence, and an
optional parent. Flow uses the parent chain to detect recursive expansion;
ownership uses it while substituting parameters forwarded through local calls.
The context exposes the existing source-span call identity through a common
operation. It is an internal analysis fact and adds no field to
`ProjectAnalysis`, `FlowAnalysis`, or their JSON schemas.

Definition indexes are generation-local. Flow rebuilds one after every source
snapshot and ownership rebuilds one for every new `ProjectCallGraph`. Source
locations are internal metadata on ownership summaries, so matching definition
evidence can be compared without changing logical `FunctionId` equality.

This migration deliberately preserves ambiguity. Duplicate definitions,
multiple inherited candidates, incomplete mapping selections, dynamic
receivers, and unsupported callable values remain unavailable or explicit
boundaries according to the consuming analyzer's existing rules.

## Shared lexical scope facts: fourth migration

`scope_facts.py` collects immutable `LexicalScopeFacts` from AST bodies. The
facts distinguish names that are loaded, bound, declared `global`, and declared
`nonlocal`. Flow uses them to compute closure captures and initialize local
environments. Ownership's literal-mapping analysis uses the same collector to
identify names whose rebinding, loop assignment, or exception assignment must
invalidate a callable mapping.

The collector does not resolve a binding or assign an owner. Two explicit
compatibility policies preserve the pre-extraction behavior:

- `FLOW_SCOPE` includes root parameters, comprehension targets, and names read
  inside nested lambda expressions. It leaves global/nonlocal stores in the
  bound-name view; Flow's capture rule handles declared nonlocals separately.
- `MAPPING_SCOPE` excludes global/nonlocal declarations, lambda bodies, and
  ordinary comprehension-local targets. Assignment-expression targets inside
  comprehensions and except-handler targets remain surrounding-body bindings.

These differences are documented compatibility behavior, not claims about a
complete Python compiler symbol table. Correcting either policy requires an
independent precision change with ground truth. Flow caches facts by AST node
within one source generation and clears that cache whenever `_index()` reads a
new snapshot. Neither facts nor cache state appear in public results.

## Shared call bindings and return substitution: fifth migration

`return_resolution.py` normalizes the values supplied to one formal parameter
or lexical capture as immutable `CallBinding` facts. `ReturnCall` connects those
bindings to one exact call occurrence and an optional local function summary.
The shared solver then substitutes parameter and capture dependencies through
local return summaries until the result converges or reaches an explicit
budget. Output paths, exclusions, relation precedence, evidence order,
conditions, and call-context IDs retain the existing `flow-0.2` behavior.

The layer is owner-neutral. Dependency payloads remain dictionaries owned by
the value-flow adapter. The solver routes their dependency kind, source,
relation, and element paths and concatenates opaque evidence, condition, and
call-context sequences without interpreting their contents. It does not
collect returns, infer effects, resolve a callee, classify a library, or decide
the owner of a value. Flow adapts its existing `FlowCall` records to
`ReturnCall` and preserves the public `trace_parameter()` result schema. Its
fixed-point limits remain 32 rounds and 2,048 distinct dependencies per
function; reaching either limit remains an explicit `return_summary_limit`
boundary.

Ownership uses the same normalized binding fact when selecting the first
bounded-context value for a formal parameter. It continues to create its own
opaque source payloads and applies its existing first-value policy in
`cross_file.py`. Ownership does not invoke the return solver or `FlowAnalyzer`,
and return ownership remains part of the ownership adapter. This keeps shared
mechanics separate from the two analyzers' different questions and contracts.

## Shared container and function effect facts: sixth migration

`effect_facts.py` describes supported mutations without owning an analysis
environment. `ContainerMethodEffect` records the positional parameter names and
receiver-mutation property for exact builtin container protocols: list
`append`, list/set/dict `clear`, dict `get`, and list `pop`. Receiver shapes and
positional arity are common facts. Each adapter retains its own treatment of
keywords, starred arguments, unknown receivers, and analysis boundaries.

`function_effects()` performs an all-or-nothing extraction over a straight-line
function body. It currently recognizes list `append`, container `clear`, and a
direct assignment to a declared nonlocal name. Each immutable `FunctionEffect`
keeps the target name, optional source name, and statement used for evidence.
Generators, control flow, unsupported calls, and other statements return no
summary; a partial effect list is never applied as though it were complete.

Flow applies these facts to its dependency environment and continues to produce
its existing `effects` and `mutation_flows` records. Ownership's `MappingFacts`
uses the shared dict `get` contract to preserve a proven read-only mapping and
retains conservative invalidation for mutating or unsupported calls. The shared
layer does not mutate either environment, identify heap aliases, or classify
call ownership. Public ownership and `flow-0.2` schemas are unchanged.

## Shared import syntax facts: seventh migration

`import_facts.py` converts each `import` or `from ... import ...` statement into
ordered immutable `ImportFact` records. A record retains the raw imported name,
explicit alias, from-module, relative level, and wildcard status. Relative
module resolution is a pure operation over the current module name and whether
the source file is a package initializer.

The record exposes two binding names because the adapters intentionally retain
different compatibility behavior for `import package.sub` without an alias.
Flow uses Python's root binding (`package`), while ownership continues to retain
its existing full dotted binding (`package.sub`). Explicit aliases and
from-import bindings agree. Encoding both choices in one syntax fact makes the
difference visible instead of embedding separate AST loops in each analyzer.

Flow uses the facts for its module import index and function-local import
environment. Ownership uses them in its import visitors and keeps its existing
wildcard, scope-binding, symbol provenance, and owner policies. The shared layer
does not decide whether an imported module is local or external, resolve a
wildcard export, choose a callee, or emit analysis boundaries. Public outputs
remain unchanged.

## Migration closure and dependency invariants

The shared program-fact layer now consists of `program_facts.py`,
`source_snapshot.py`, `call_resolution.py`, `scope_facts.py`,
`return_resolution.py`, `effect_facts.py`, and `import_facts.py`. These modules
may depend on one another and on the Python standard library. They must
not import the ownership adapters, `flow.py`, classification, CLI, or view
layers. `tests/test_shared_layer_boundaries.py` enforces this direction and also
checks that both analyzer sides consume the complete shared layer through
explicit imports.

Two remaining syntax operations were consolidated during closure. Yield
detection now comes from `effect_facts.contains_yield()` for both generator
summaries and effect eligibility. Lexical capture selection now comes from
`scope_facts.captured_names()`; Flow still supplies its definition index and
call-time dependency values.

The migration deliberately ends at facts and pure substitution. Ownership and
value flow retain separate environments, source payloads, definition
collection, dispatch policies, boundaries, evidence schemas, and public result
types. The private ownership call graph is not exposed as the value-flow call
chain. A shared `AnalysisSession` may later avoid duplicate work when a
downstream consumer runs both analyzers, but it is not required for correctness.
A production session would need an immutable source generation plus separate
ownership and flow decoding/module-index views; passing one mutable
`SourceStore` to both analyzers is not sufficient. Such a session would be an
additive public API, while the existing constructors and result schemas remain
available.

Before a migration, capture fingerprints of the complete public ownership views
for the 42-project corpus and flow snapshots plus declared parameter queries for
the evaluation matrix. Compare on the same checkout path and Python runtime:

```bash
python scripts/compare_analysis_baseline.py --output before.json
# Apply the internal migration.
python scripts/compare_analysis_baseline.py --output after.json --compare before.json
```

The comparison exits nonzero on changed output or call inventory. Per-entry
timings are recorded separately and excluded from output fingerprints. The
script restarts with `PYTHONHASHSEED=0` when needed so set-derived explanation
order does not produce false differences between processes. This
check supplements ground-truth and semantic regression tests; unchanged output
does not establish complete static-analysis precision.

## Per-Layer Data Structures

### Scanner → Project file list
- `scanner.py` produces a list of absolute file paths.
- `module_mapper.py` maps each file to a dotted module name (e.g., `pkg/sub.py` → `pkg.sub`).
- For an explicit ownership source-file input, `module_mapper.py` indexes only
  that file and bypasses directory scanning. Its mapping root is the parent
  directory, lifted above enclosing regular packages to retain package names.
  `cross_file.py` runs the same ownership pipeline and returns `ProjectAnalysis`
  using that root; no sibling sources are added.
- Source selection and module naming supply the analysis context. File and
  directory inputs with the same source set and mapping root use identical
  ownership semantics. Missing imported implementations limit both input
  forms; file selection does not introduce a separate classification policy.

### Single-File Analysis (`single_file.py`)

`SingleFileAnalyzer` is an `ast.NodeVisitor` that produces:

| Output | Type | Purpose |
|--------|------|---------|
| `symbols.direct` | `dict[str, object]` | Module-level name → source compatibility mapping |
| `symbols.chains` | `dict[str, list]` | Name → resolution chain |
| `api_calls` | `list[dict]` | Legacy call records (keyed by `api`, `top`, `base`, `chain`, ...) |
| `call_site_objects` | `list[CallSite]` | Typed call-site IR collected in parallel with `api_calls` |
| `symbol_refs` | `list[SymbolRef]` | Symbol references for provenance |
| `return_sources` | `dict[str, object]` | Function name → return expression source (SourceSet for multi-return) |
| `return_element_sources` | `dict[str, list]` | Qualified function name to returned-element sources, resolved under exact call contexts independently of container ownership |
| `call_graph_return_values` | `dict[str, object]` | Qualified function name to concrete return alternatives for receiver-protocol queries, including scalar and unresolved branches |
| `call_sites` | `dict[str, list[dict]]` | Function name → context-sensitive call-site parameter sources |
| `function_params` | `dict[str, list[str]]` | Function name → parameter name list |
| `defined_functions` | `set[str]` | Names of locally defined functions |
| `import_from_symbols` | `dict[str, str]` | Import alias → fully qualified name |
| `instance_attrs` | `dict[(class, attr), source]` | `(ClassName, self.attr)` → constructor-propagated source |

### Cross-File Analysis (`cross_file.py` + extracted sub-modules)

`ProjectAnalyzer` orchestrates:

1. **Parse**: Iterates files, creates `SingleFileAnalyzer` per file.
2. **Resolve**: `resolve_cross_file_symbols()` traces each symbol through imports/assignments across modules, populating `global_symbols` and `symbol_chains`.
3. **SourceSet convergence**: `SourceSetResolver` in `source_resolution.py` resolves multi-source bindings with origin-aware rules.
4. **Classify**: `ClassificationPipeline` in `classification.py` assigns reason, confidence, and alternatives via priority-ordered rules.
5. **Provenance**: `_build_symbol_provenance()` traces each `SymbolRef` into a `SymbolProvenance`.
6. **Library Usage**: `build_library_usage()` in `library_usage.py` aggregates calls and provenance by `top_library`.
7. **Decorator evidence**: `build_decorator_index()` / `lookup_decorated_by()` in `decorator_provenance.py` populate `ApiCall.decorated_by`.
8. **Bounded call graph**: `call_graph.py` holds `FunctionSummary` /
   `ClassSummary` / `CallEdge` facts and supplies exact project-local call
   contexts for parameter, return, receiver, and iterable-element propagation.
   `FunctionSummary.return_values` retains concrete protocol evidence separately
   from provenance-oriented `returns`, including possible implicit returns.
   `mapping_facts.py` preserves local callable identities selected from literal
   dictionaries. These private facts share lexical bindings, invalidate on
   mutation or escape, and do not replace container ownership sources. These
   call-graph facts are internal analysis evidence and are not a separate field
   in `ProjectAnalysis` or the public JSON schema.

Output: `ProjectAnalysis`

| Field | Purpose |
|-------|---------|
| `files` | Per-file `FileAnalysis` (symbols, chains, api_calls, provenance) |
| `all_api_calls` | Flat list of every `ApiCall` across all files |
| `all_symbol_provenance` | Flat list of every `SymbolProvenance` |
| `library_usage` | `dict[library → LibraryUsage]` with counts, files, imports |
| `diagnostics` | Parse/read errors |
| `stats` | Parsed, skipped, and total module counts |

## Lexical Scope Semantics

Ownership analysis uses a lexical scope model. Function parameters, local variables,
class-body names, and comprehension targets remain in their defining scopes.
Module-level `SymbolTable.direct` is retained as a compatibility bridge for
cross-file resolution, but function-local bindings never overwrite it.

Name lookup walks the active lexical scope chain, class-parent scopes are
skipped where Python method lookup requires it, and branch snapshots merge
competing sources conservatively through `SourceSet`.

## Legacy Compatibility Paths

Compatibility surfaces still present in the codebase:

| Surface | Current Status | Notes |
|---------|---------------|-------|
| `SymbolTable.direct` | Still used as module-level fallback | Lexical bindings live in `Scope.bindings`; `direct` is a module bridge |
| `api_calls` (dict list) | Still the primary single-file output | Typed `CallSite` collected in parallel |
| `return_sources` (SourceSet) | Multi-return tracking via `SourceSet` + CallGraph | Current default |
| `_base_top_source()` | Wraps `ClassificationPipeline.classify()` | Current default |
| Instance attr propagation | Constructor arg → self.attr tracking | Bounded local hierarchy support; no full Python MRO or dynamic descriptors |
| `--json` (dataclass dump) | Replaced by full provenance schema | 1.0.4+ default |

## Resolution Boundaries

- `_resolve_structured_source()` dispatches the typed Source IR, including
  container items and iteration, tuple fields, instance methods and attributes,
  parameter sources, Python shapes, `super()` methods, call results, and derived
  results. `SourceSet` convergence is handled by
  `source_resolution.py::SourceSetResolver`. The non-SourceSet branches still
  live inline here.

- `trace_symbol()` is the trace orchestration hotspot, mixing cross-module symbol lookup with wildcard import resolution and parameter back-tracing.  Call-graph facts (`call_graph.py`) feed into it for return-object and arg-source propagation.

- `_build_symbol_provenance()` passes `_direct_source=ref.source` for all SymbolRefs, enabling per-assignment provenance even when module-level reassignment overwrites the symbol table.
