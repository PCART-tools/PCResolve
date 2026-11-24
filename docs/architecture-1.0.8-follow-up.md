# Architecture follow-up: 1.0.8

This note records the state and proof boundaries made explicit in the 1.0.8
architecture follow-up. It supplements [the architecture overview](architecture.md)
and the frozen compatibility baseline in `tests/baselines/architecture_1_0_8/`.

## State ownership and data movement

| Component | Owns | Captures or returns | Boundary |
|---|---|---|---|
| `SingleFileAnalyzer` | One module visitor's mutable collection state | Source-derived fields declared by `SingleFileVisitorFacts` | Traversal stacks and lookup/query caches are run-local and excluded from reusable facts |
| `SingleFileFacts` | Reusable facts from one source snapshot | Explicit visitor fields, detached fact structures, and callback-edge records | Cloning rebinds callbacks to the new visitor; the AST remains associated with its `SourceDocument` |
| `FlowAnalyzer` | Source index and one analysis invocation | Public `FlowAnalysis` output | Ownership and flow keep separate snapshots, state, propagation and result schemas |
| `_Summary` | One function summary's query-local environment, budget/depth, calls and effects | Child summaries and transfer evidence | `_make_child_summary()` provides the recursive construction point; context cleanup keeps its established `try/finally` handling |
| `_CallExpressionState` | One call expression's mutable facts across ordered transfer phases | Internal phase inputs and outputs | Internal only; it does not change public objects or JSON schemas |
| `_DeferredClassProofState` | Evidence and bounded interpreter state for one proof attempt | Declaration effects and provenance evidence | A failed precondition, exhausted budget, or unsupported effect yields no proof |

Ownership facts are reusable only for the source version that produced them.
Edits, deletion, and renames select a new snapshot and invalidate the affected
facts. A cloned visitor receives independent mutable structures and listener
callbacks. The cache schema is explicit: adding a visitor attribute does not
silently add it to the cache.

For value flow, `_Summary._make_child_summary()` takes the current result,
function reference, syntax node, remaining depth, optional receiver class, and
incoming bindings. Recursive calls therefore pass through an explicit factory
method instead of relying on a module global injected after import. Each child
owns fresh query-local state while the analyzer's source index remains shared
within the analysis.

## Deferred class proof stages

`prepare()` now exposes the proof lifecycle through three pieces:

1. `_within_function_budget()` rejects syntax beyond 2,000 AST nodes and
   charges the optional run budget. Budget exhaustion propagates as the
   established `AnalysisLimitExceeded` boundary.
2. `_DeferredClassProofState` owns bindings used for class aliases and dirty
   names, evidence collections, metadata publication/invalidation, namespace
   guard results, and the expression budget. The `block()` interpreter still
   processes statements in source order and merges branch bindings
   conservatively.
3. Evidence construction runs only after the declaration effects are bounded.
   It aggregates supporting source hashes and assumptions, strips private
   bookkeeping tokens from public proof evidence, and returns the transformed
   effect-only syntax plus proof record.

Function bodies remain deferred. Unsupported calls, escaping functions,
unsupported control flow, unstable namespaces, and failed effect checks do not
gain an execution exemption. Later writes to a retained function's metadata
invalidate earlier stored snapshots. These changes organize existing proof
state and limits; they do not add inference rules.

## Follow-up refactor record

| Previously implicit or broad mechanism | Current boundary | Remaining structure and reason |
|---|---|---|
| `_Summary` installed into sibling modules through `sys.modules` and `setattr` | Explicit `_make_child_summary()` factory method | `_Summary` still composes transfer mixins over one query-local state; a wholesale rewrite would widen the semantic diff |
| Dynamic `SimpleNamespace` for call-transfer phases | `_CallExpressionState` with an explicit `__slots__` field inventory | Phase-specific values are heterogeneous; the explicit field inventory makes additions reviewable without a new public schema |
| Visitor-wide `__dict__` capture and exclusion lists | Declared `SingleFileVisitorFacts` fields | `_detach_visitor_callbacks()` still traverses nested fact-object attributes to find listener edges. That traversal detaches callbacks; it does not decide which visitor fields are cached |
| Repeated module-local namespace injection | Direct implementation imports at package boundaries | Existing mixin composition remains in ownership and flow so lexical traversal and query state keep their current owners |
| Legacy flat import paths | Lazy compatibility registry and frozen 56-path comparison | The shim remains for 1.0.8 compatibility; internal imports target implementation modules directly |
