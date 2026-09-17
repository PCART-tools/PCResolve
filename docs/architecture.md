# PCResolve Architecture

PCResolve's primary analysis surface is call-site ownership, supported by symbol
provenance. `all_api_calls` is the primary classification output.
`all_symbol_provenance` explains the symbol flows that support those call
classifications. The experimental `FlowAnalyzer` separately exposes parameter,
return, and effect evidence for downstream analyses.

## Pipeline Overview

```
scanner.py  →  module_mapper.py  →  single_file.py  →  cross_file.py  →  cli.py  →  views.py
                                        ↑                    ↑
                                   symbol_table.py    source_resolution.py
                                   scope.py           classification.py
                                   sources.py         library_usage.py
                                   ir.py              decorator_provenance.py
                                   types.py           call_graph.py
                                                      call_resolution.py
                                                      scope_facts.py
                                                      return_resolution.py
                                   diagnostics.py
```

## Layer Summary

| Layer | Module | Input | Output |
|-------|--------|-------|--------|
| Scan | `scanner.py` | Project root path | List of `.py`/`.pyi` files (excluding venv) |
| Module map | `module_mapper.py` | File list | File path ↔ dotted module name |
| Parse + single-file | `single_file.py` | Source code | `SymbolTable`, api_calls (dict list), `call_site_objects`, `symbol_refs` |
| Cross-file | `cross_file.py` | Per-file tracers | `ProjectAnalysis` (global symbols, chains, api calls, provenance, library usage) |
| Shared syntax and binding | `program_facts.py` | AST positions, signatures, opaque argument payloads | Source spans and pure binding projections |
| Shared source versions | `source_snapshot.py` | Explicit file set and read/naming policies | Source snapshots, cached ASTs, read-only module index |
| Shared definition lookup | `call_resolution.py` | Adapter-collected definitions and call occurrences | Ordered candidate index and parent-linked call contexts |
| Shared lexical facts | `scope_facts.py` | Function/lambda AST or one statement body | Immutable loaded, bound, global, and nonlocal name sets |
| Shared return substitution | `return_resolution.py` | Normalized call bindings and adapter-owned dependency records | Bounded, composed return dependencies |
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
does not invoke `FlowAnalyzer`. Import resolution, target resolution, lexical
facts, return substitution, captures, and effects are migrated independently;
later sections describe completed stages.

## Shared source snapshots and module index: second migration

`source_snapshot.py` supplies source versions and module naming to both
analyzers. `ProjectAnalyzer` and `FlowAnalyzer` each own a `SourceStore` for their
session. The layer has no dependency on analysis summaries or classification.
A future shared analysis session can supply one store to both internal adapters;
this migration adds no public constructor option or output field.

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
- `ModuleMapper` preserves its mutable compatibility lookups and scan order.
  Its private index describes the current scan; existing cumulative lookup
  behavior across rescans remains until the session/invalidation migration.

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
2. **Resolve**: `resolve_cross_file_symbols()` traces each symbol through imports/assignments across modules, populated `global_symbols` and `symbol_chains`.
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
