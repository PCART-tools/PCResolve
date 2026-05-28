# PCResolve Architecture

## Pipeline Overview

```
scanner.py  →  module_mapper.py  →  single_file.py  →  cross_file.py  →  cli.py / views.py
                                        ↑
                                   symbol_table.py    types.py    sources.py
                                   scope.py           ir.py       diagnostics.py
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

### Cross-File Analysis (`cross_file.py`)

`ProjectAnalyzer` orchestrates:

1. **Parse**: Iterates files, creates `SingleFileAnalyzer` per file.
2. **Resolve**: `resolve_cross_file_symbols()` traces each symbol through imports/assignments across modules, populates `global_symbols` and `symbol_chains`.
3. **Classify**: `get_calls()` classifies each API call by resolving its base through the global symbol table.
4. **Provenance**: `_build_symbol_provenance()` traces each `SymbolRef` into a `SymbolProvenance`.
5. **Library Usage**: `_build_library_usage()` aggregates calls and provenance by `top_library`.

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

| Behavior | v1 (default) | v2 (lexical scopes) |
|----------|-------------|---------------------|
| Function params | Written to module `symbols.direct` | Only in function scope |
| Local variables | Written to module `symbols.direct` | Only in function scope |
| Comprehension vars | Written to module `symbols.direct` | Only in comprehension scope |
| CallResult callee | Raw name (e.g., `"nx"`) | Scope-resolved name (e.g., `"networkx"`) |
| `get_base` (non-call-lookup) | Returns name | Returns scope binding source |
| `get_base` (call_lookup=True) | Returns name | Returns name (kept raw for CallResult) |

v2 is the default as of 1.0.4. v2 fixes scope pollution and no longer produces dataclass repr or structured source display strings as library keys. v1 is available via `--scope-model v1` for legacy comparison.

## Legacy Compatibility Paths

The following paths exist for backward compatibility and will be replaced:

| Current | Replaced By | Phase |
|---------|-------------|-------|
| `SymbolTable.direct` (single-slot) | `Scope.bindings` (per-scope binding; SourceSet in Phase 5) | 3 (partial), 5 (SourceSet) |
| `api_calls` (dict list) | `call_site_objects` (typed `CallSite`) | 4A (parallel), 9 (full migration) |
| `return_sources` (single value) | `SourceSet` + CallGraph | 5, 7A |
| `call_sites`/`function_params` (ad-hoc param tracing) | CallGraph propagation | 7A |
| `_base_top_source()` classification | `ClassificationPipeline` | 8B |
| Instance attr propagation (`instance_attrs`) | 7B class/instance method resolution | 7B |
| Legacy `--json` (dataclass dump) | `--json` (full provenance, 1.0.4+) | 4D (see output-contract.md) |

## Known Patch Zones

- `_resolve_structured_source()` handles four source kinds (container_item, instance_method, container_iter, call_result) with significant branching. Future: `SourceResolver` component in Phase 9.

- `trace_symbol()` mixes tracing with wildcard import resolution and parameter back-tracing. Future: `SymbolTracer` with separate `CallGraph` propagation.

- `_build_symbol_provenance()` passes `_direct_source=ref.source` for all SymbolRefs, enabling per-assignment provenance even when module-level reassignment overwrites the symbol table.
