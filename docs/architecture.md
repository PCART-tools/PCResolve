# PCResolve Architecture

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
| `symbols.direct` | `dict[str, object]` | Name → source mapping (module-level or v1 all-level) |
| `symbols.chains` | `dict[str, list]` | Name → resolution chain |
| `api_calls` | `list[dict]` | Legacy call records (keyed by `api`, `top`, `base`, `chain`, ...) |
| `call_site_objects` | `list[CallSite]` | New typed call-site IR (parallel to api_calls) |
| `symbol_refs` | `list[SymbolRef]` | Symbol references for provenance |
| `return_sources` | `dict[str, object]` | Function name → return expression source (SourceSet since Phase 5) |
| `call_sites` | `dict[str, list[dict]]` | Function name → call-site parameter sources (for ad-hoc param tracing) |
| `function_params` | `dict[str, list[str]]` | Function name → parameter name list |
| `defined_functions` | `set[str]` | Names of locally defined functions |
| `import_from_symbols` | `dict[str, str]` | Import alias → fully qualified name |
| `instance_attrs` | `dict[(class, attr), source]` | `(ClassName, self.attr)` → source (v2 constructor propagation) |

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

Output: `ProjectAnalysis`

| Field | Purpose |
|-------|---------|
| `files` | Per-file `FileAnalysis` (symbols, chains, api_calls, provenance) |
| `all_api_calls` | Flat list of every `ApiCall` across all files |
| `all_symbol_provenance` | Flat list of every `SymbolProvenance` |
| `library_usage` | `dict[library → LibraryUsage]` with counts, files, imports |
| `diagnostics` | Parse/read errors |
| `stats` | Module counts, scope model |

## Scope Model (v1 vs v2)

| Behavior | v1 (legacy) | v2 (default, lexical scopes) |
|----------|-------------|---------------------|
| Function params | Written to module `symbols.direct` | Only in function scope |
| Local variables | Written to module `symbols.direct` | Only in function scope |
| Comprehension vars | Written to module `symbols.direct` | Only in comprehension scope |
| CallResult callee | Raw name (e.g., `"nx"`) | Scope-resolved name (e.g., `"networkx"`) |
| `get_base` (non-call-lookup) | Returns name | Returns scope binding source |
| `get_base` (call_lookup=True) | Returns name | Returns name (kept raw for CallResult) |

v2 is the default as of 1.0.4. v2 fixes scope pollution and no longer produces dataclass repr or structured source display strings as library keys. v1 is available via `--scope-model v1` for legacy comparison.

## Legacy Compatibility Paths

Compatibility surfaces still present in the codebase:

| Surface | Current Status | Notes |
|---------|---------------|-------|
| `SymbolTable.direct` | Still used as module-level fallback | Scope model writes to `Scope.bindings`; `direct` is compat bridge |
| `api_calls` (dict list) | Still the primary single-file output | Typed `CallSite` collected in parallel |
| `return_sources` (SourceSet) | Upgraded to `SourceSet` + CallGraph | Phase 5 / 7B-full complete |
| `_base_top_source()` | Wraps `ClassificationPipeline.classify()` | Phase 8B complete |
| Instance attr propagation | 7B-lite constructor arg tracking | Full class-aware receiver resolution deferred |
| `--json` (dataclass dump) | Replaced by full provenance schema | 1.0.4+ default |

## Known Patch Zones

- `_resolve_structured_source()` dispatches `container_item`, `instance_method`, `container_iter`, `call_result`.  `SourceSet` convergence is handled by `source_resolution.py::SourceSetResolver`.  The non-SourceSet branches still live inline here.

- `trace_symbol()` is the trace orchestration hotspot, mixing cross-module symbol lookup with wildcard import resolution and parameter back-tracing.  Call-graph facts (`call_graph.py`) feed into it for return-object and arg-source propagation.

- `_build_symbol_provenance()` passes `_direct_source=ref.source` for all SymbolRefs, enabling per-assignment provenance even when module-level reassignment overwrites the symbol table.
