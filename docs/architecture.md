# PCResolve Architecture

PCResolve has two connected analysis surfaces: call-site ownership and symbol provenance. `all_api_calls` is the primary classification output. `all_symbol_provenance` explains the symbol flows that support those call classifications.

## Pipeline Overview

```
scanner.py  →  module_mapper.py  →  single_file.py  →  cross_file.py  →  cli.py  →  views.py
                                        ↑                    ↑
                                   symbol_table.py    source_resolution.py
                                   scope.py           classification.py
                                   sources.py         library_usage.py
                                   ir.py              decorator_provenance.py
                                   types.py           call_graph.py
                                   diagnostics.py
```

## Layer Summary

| Layer | Module | Input | Output |
|-------|--------|-------|--------|
| Scan | `scanner.py` | Project root path | List of `.py`/`.pyi` files (excluding venv) |
| Module map | `module_mapper.py` | File list | File path ↔ dotted module name |
| Parse + single-file | `single_file.py` | Source code | `SymbolTable`, api_calls (dict list), `call_site_objects`, `symbol_refs` |
| Cross-file | `cross_file.py` | Per-file tracers | `ProjectAnalysis` (global symbols, chains, api calls, provenance, library usage) |
| Views | `views.py` | `ProjectAnalysis` | Dict/list for JSON serialization |
| CLI | `cli.py` | Project root + args | Human-readable text or JSON |

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
| `call_site_objects` | `list[CallSite]` | New typed call-site IR (parallel to api_calls) |
| `symbol_refs` | `list[SymbolRef]` | Symbol references for provenance |
| `return_sources` | `dict[str, object]` | Function name → return expression source (SourceSet for multi-return) |
| `return_element_sources` | `dict[str, list]` | Qualified function name to returned-element sources, resolved under exact call contexts independently of container ownership |
| `call_graph_return_values` | `dict[str, object]` | Qualified function name to concrete return alternatives for receiver-protocol queries, including scalar and unresolved branches |
| `call_sites` | `dict[str, list[dict]]` | Function name → call-site parameter sources (for ad-hoc param tracing) |
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
8. **Call graph**: `call_graph.py` holds `FunctionSummary` / `ClassSummary` / `CallEdge` facts.
   `FunctionSummary.return_values` retains concrete protocol evidence separately
   from provenance-oriented `returns`, including possible implicit returns.
   `mapping_facts.py` preserves local callable identities selected from literal
   dictionaries. These private facts share lexical bindings, invalidate on
   mutation or escape, and do not replace container ownership sources.

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

PCResolve uses one lexical scope model. Function parameters, local variables,
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
| Instance attr propagation | Constructor arg → self.attr tracking | Full class-aware receiver resolution is future work |
| `--json` (dataclass dump) | Replaced by full provenance schema | 1.0.4+ default |

## Known Patch Zones

- `_resolve_structured_source()` dispatches `container_item`, `instance_method`, `container_iter`, `call_result`.  `SourceSet` convergence is handled by `source_resolution.py::SourceSetResolver`.  The non-SourceSet branches still live inline here.

- `trace_symbol()` is the trace orchestration hotspot, mixing cross-module symbol lookup with wildcard import resolution and parameter back-tracing.  Call-graph facts (`call_graph.py`) feed into it for return-object and arg-source propagation.

- `_build_symbol_provenance()` passes `_direct_source=ref.source` for all SymbolRefs, enabling per-assignment provenance even when module-level reassignment overwrites the symbol table.
