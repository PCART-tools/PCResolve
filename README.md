# PCResolve — Python Third-Party Library Usage Provenance Analyzer

Static analysis tool for Python projects. Answers:
*what third-party libraries does this project use, through which
symbols, call chains, return values, and container propagation paths?*

Two core provenance objects:
- **API call provenance** — every call expression classified as
  `local`, `python`, or a specific top-level library.
- **Symbol provenance** — variables, return values, class instances,
  attributes, container elements traced to their origin libraries.

[![PyPI](https://img.shields.io/pypi/v/pcresolve)](https://pypi.org/project/pcresolve/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
pip install pcresolve        # >= 1.0.4
```

Zero third-party dependencies — Python 3.9+ standard library only.

## Quick Start (1.0.4)

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

### JSON Output (`--json`)

```json
{
  "schema_version": "1.0",
  "profile": "full",
  "all_api_calls": [{
    "expression": "np.array([1,2,3])",
    "top_library": "numpy",
    "reason": "DIRECT_IMPORT",
    "confidence": 1.0,
    "alternatives": [],
    "decorated_by": [],
    "file_path": "main.py",
    "lineno": 4
  }],
  "all_symbol_provenance": [],
  "library_usage": {}
}
```

## PCART Integration

```
确定纳入:  call.top_library == target_library
候选纳入:  target_library in call.alternatives
          target_library in call.decorated_by
排除:     call.top_library in (local, python, unknown)
          AND target_library not in alternatives/decorated_by
```

See `docs/pcart-integration.md` for details.

## Supported Patterns

- Direct import / `from`/`as` / alias calls
- Variable binding, container storage (dict, list, tuple, set)
- `partial` / lambda wrappers
- Class encapsulation, constructor arg → `self.attr` propagation
- Decorator provenance (`decorated_by` evidence, target stays `local`)
- Context managers (`with`, `async with`)
- Chained calls / fluent API, `getattr` / `import_module`
- Container iteration with merged alternatives
- Multi-return tracking with SourceSet alternatives
- Cross-file symbol propagation, wildcard import, re-export

## Breaking Changes (1.0.4)

- **Default scope model**: `v1` → `v2` (lexical scopes).
- **`--json` output**: legacy dataclass dump → full provenance schema
  with `profile`, `reason`, `confidence`, `alternatives`, `decorated_by`.
- **Pre-1.0.4 JSON**: experimental, no backward compatibility guarantee.
- Use `--scope-model v1` for legacy behavior.

## Known Limitations

- Multiple return paths with different third-party libraries produce
  conservative primary (`local`) with complete alternatives.
- Dynamic `import_module(name)` only resolves string-literal names.
- `@classmethod` / `@staticmethod` / descriptor / property resolution
  is deferred to future releases.

## Running Tests

```bash
python -m pytest tests/ -v
```

## License

PCResolve is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
