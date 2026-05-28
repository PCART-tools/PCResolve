# PCResolve — Python Project-Level Third-Party Library Usage Provenance Analyzer

PCResolve is an explainable static analysis engine that answers:
*which third-party libraries does a Python project use, and through
which imports, symbols, call chains, return values, and container
propagation paths?*

It is designed for CI pipelines, IDE integration, audit workflows,
and large-scale codebase scanning.  Every classification comes with
a traceable chain, a reason, a confidence score, and alternatives
when the analysis cannot decide between multiple candidates.

Zero runtime third-party dependencies.  Python 3.9+.

[![PyPI](https://img.shields.io/pypi/v/pcresolve)](https://pypi.org/project/pcresolve/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Why PCResolve

`import numpy as np` is just the entry point.  The real question is:
how does `np` become `df`, how does `df` flow into function
parameters, how does a method return a pandas object through three
layers of local wrappers, and how does a container element carry
library provenance through iteration?

PCResolve tracks two kinds of provenance:

| Object | Question |
|--------|----------|
| **API call provenance** | Which top-level library does this call expression belong to? |
| **Symbol provenance** | Where did this variable / return value / attribute / container element come from? |

## What It Produces

| Output | Description |
|--------|-------------|
| `all_api_calls` | Every call expression with `top_library`, `reason`, `confidence`, `alternatives`, `decorated_by`, trace chain, and source location. |
| `all_symbol_provenance` | Per-symbol origin records: import aliases, variable assignments, function returns, parameters, attributes, container items, decorator evidence. |
| `library_usage` | Aggregated per-library index with call/symbol counts, file lists, reason distributions, and confidence ranges. |
| `diagnostics` | Structured parse errors, encoding failures, and trace warnings (non-fatal by default). |

## Quick Start

### Installation

```bash
pip install pcresolve        # >= 1.0.4
```

### CLI

```bash
pcresolve /path/to/project                         # human summary (v2 default)
pcresolve /path/to/project --json                  # full provenance JSON
pcresolve /path/to/project --json-summary          # compact CI summary
pcresolve /path/to/project --explain-library numpy
pcresolve /path/to/project --explain-call "np.array"
pcresolve /path/to/project --scope-model v1        # legacy mode
```

### Library API

```python
from pcresolve import analyze_project

result = analyze_project("/path/to/project")
for call in result.all_api_calls:
    print(f"{call.expression} -> {call.top_library}")
    print(f"  reason={call.reason} confidence={call.confidence}")
    print(f"  alternatives={call.alternatives}")
```

## Output Profiles

| Flag | Profile | Use Case |
|------|---------|----------|
| *(default)* | Human summary | Terminal browsing |
| `--json` | Full provenance | Machine consumption, debugging |
| `--json-summary` | Compact aggregate | CI pipelines, dashboards |
| `--debug-dump` | Legacy full text | Debugging |

## 1.0.4 Stable Contract

PCResolve 1.0.4 is the first stable provenance contract release.
JSON outputs before 1.0.4 are experimental and not guaranteed
compatible.

### JSON output excerpt (`--json`)

Abbreviated for readability; see `docs/output-contract.md` for the
complete stable field list.

```json
{
  "schema_version": "1.0",
  "profile": "full",
  "project_root": ".",
  "stats": {
    "total_modules": 4,
    "parsed_modules": 4,
    "skipped_modules": 0,
    "scope_model": "v2",
    "api_call_count": 18,
    "library_count": 3
  },
  "diagnostics": [],
  "files": [{
    "file_path": "main.py",
    "module_name": "main",
    "api_calls": [{
      "expression": "np.array([1,2,3])",
      "func_name": "np.array",
      "parameters": "[1,2,3]",
      "top_library": "numpy",
      "reason": "DIRECT_IMPORT",
      "confidence": 1.0,
      "alternatives": ["numpy"],
      "decorated_by": [],
      "file_path": "main.py",
      "lineno": 4,
      "col_offset": 0,
      "end_lineno": 4,
      "end_col_offset": 18,
      "chain": ["np.array([1,2,3])", "np", "numpy"],
      "resolved_func": "numpy.array",
      "resolved_chain": ["np.array", "numpy.array", "numpy"]
    }],
    "symbol_provenance": [{
      "symbol": "np",
      "kind": "import",
      "top_library": "numpy",
      "reason": "DIRECT_IMPORT",
      "confidence": 1.0
    }]
  }],
  "all_api_calls": [
    {
      "expression": "np.array([1,2,3])",
      "top_library": "numpy",
      "reason": "DIRECT_IMPORT",
      "confidence": 1.0,
      "alternatives": ["numpy"],
      "decorated_by": [],
      "file_path": "main.py",
      "lineno": 4
    }
  ],
  "all_symbol_provenance": [
    {
      "symbol": "np",
      "kind": "import",
      "top_library": "numpy",
      "reason": "DIRECT_IMPORT",
      "confidence": 1.0
    }
  ],
  "library_usage": {
    "numpy": {
      "library": "numpy",
      "api_call_count": 6,
      "symbol_count": 3,
      "files": ["main.py", "utils.py"],
      "imports": ["np"],
      "reason_counts": { "DIRECT_IMPORT": 6, "RETURN_PROPAGATION": 3 },
      "kind_counts": { "import": 2, "variable": 4 },
      "has_evidence": true,
      "min_confidence": 0.9,
      "max_confidence": 1.0
    }
  }
}
```

### Contract highlights

- **Default scope model**: `v2` (lexical scopes).  `--scope-model v1` available.
- **Path normalization**: all paths are relative POSIX (`/`).  External paths use `<external>/...`.
- **`alternatives`**: individual third-party library names.  No merged display labels.
- **`decorated_by`**: list of library names that decorate the call target.  Filtered: no `local`/`python`/`unknown`.
- **`reason`** and **`confidence`**: every call has both.  See `docs/output-contract.md` for the full table.

### Breaking changes from pre-1.0.4

- Default `scope_model` changed from `v1` to `v2`.
- `--json` changed from legacy dataclass dump to full provenance schema.
- `--json-stable` deprecated and hidden.
- Pre-1.0.4 JSON is experimental; no backward compatibility.

## Supported Analysis Patterns

### Imports

Direct imports, `from`/`as` aliases, wildcard imports, cross-file
re-exports, transitive imports through local modules.

### Data Propagation

Variable assignment, function return values, parameter binding at
call sites, constructor argument → `self.attr` → method call
propagation, container item access (dict subscript, list index).

### Containers

Dict / list / tuple / set literal tracking, container iteration
(`for x in items`), merged candidates for ambiguous iteration
(reported as alternatives), container-mutating method arg-source
tracking (`append`, `extend`).

### Cross-File

Symbol tracing across module boundaries, imported local functions,
class method resolution through constructor call sites, wildcard
import resolution with candidate merging.

### Decorators

Decorator expressions counted as API calls, decorated targets
keep `local` primary identity, `decorated_by` evidence recorded
independently, stacked decorators all preserved.

### Reporting

Per-library explain views (`--explain-library`), per-symbol
provenance traces (`--explain-symbol`), per-call query matching
(`--explain-call`), library usage aggregation with reason counts
and confidence distribution.

## Architecture

```text
scanner.py → module_mapper.py → single_file.py → cross_file.py → cli.py → views.py
                                      ↑               ↑
                                symbol_table.py   source_resolution.py
                                scope.py          classification.py
                                sources.py        library_usage.py
                                ir.py             decorator_provenance.py
                                types.py          call_graph.py
                                diagnostics.py
```

| Layer | Module | Role |
|-------|--------|------|
| Scan | `scanner.py` | Discover `.py`/`.pyi` files, filter venvs |
| Map | `module_mapper.py` | File path ↔ module name |
| Parse | `single_file.py` | AST visitor, per-file symbol table, scope model |
| Trace | `cross_file.py` | Cross-module symbol resolution, call classification |
| Classify | `classification.py` | Priority-ordered classification pipeline |
| Index | `library_usage.py` | Per-library usage aggregation |
| Output | `cli.py`, `views.py` | Human, JSON full, JSON summary, explain views |

## Validation

PCResolve is continuously validated against a multi-project
regression gate:

```text
Unit tests:        557 passed, 0 failed
Hard baselines:    21 projects, 0 exceeded
Full audit:        42 real-world projects, 0 crashes, 0 illegal keys
v1/v2 differential regressions: 303 (all classified by taxonomy)
```

Key invariants enforced on every change:

- `illegal_keys == 0` — no dataclass repr or structured source
  display leaks into `top_library` or `library_usage` keys.
- All 21 hard baselines must not exceed their recorded
  regression counts.
- Golden JSON output tests lock the 1.0.4 contract.
- Diff taxonomy breaks regressions into `third_party_api_loss`,
  `local_to_unknown`, and precision changes.

## Known Limitations

PCResolve is a static analysis tool.  It is conservative by design:
when it cannot uniquely determine a library, it reports
`alternatives` rather than guessing.

| Limitation | Behavior |
|-----------|----------|
| Multi-third-party returns | Conservative primary (`local`/`unknown`), complete alternatives in `alternatives` and `library_usage`. |
| Dynamic `import_module(name)` | Only resolves string-literal arguments.  Variables produce unresolved results. |
| `@classmethod` / `@staticmethod` | Method resolution is deferred.  Treated conservatively. |
| Descriptors / properties | Not tracked.  Attribute access on descriptor results may be unresolved. |
| Runtime reflection / monkey-patching | Not modeled.  Conservative fallback. |
| Multi-threading / async control flow | Not modeled.  All reachable branches contribute to `SourceSet`. |
| Third-party library internals | Not analyzed.  Only same-project local functions and classes are traced. |

These limitations mean that `top_library` can be conservative
(`local` or `unknown`) while `alternatives` still contains the
third-party candidates.  Downstream tools should check both.

## Consuming the Output

Downstream tools should treat `top_library` as the primary
classification and `alternatives` / `decorated_by` as additional
evidence.  A call whose `top_library` is `local` or `unknown` may
still reference a third-party library through alternatives (e.g.
multi-source returns or container iteration) or decorator evidence.

For library-level aggregation, use `library_usage` which already
incorporates `alternatives` and `decorated_by` evidence.

## Development

```bash
pip install -e .

# Run tests
python -m pytest tests/ -v

# Baseline gate
python scripts/diff_v1_v2.py tests/fixtures/tested_projects/

# Full audit
python scripts/audit_tested_projects.py
```

See `docs/architecture.md` for the pipeline design,
`docs/output-contract.md` for the stable JSON schema, and
`docs/source-semantics.md` for Source IR and convergence rules.

## License

MIT.  See [LICENSE](./LICENSE) for details.
