# PCResolve

[![PyPI](https://img.shields.io/pypi/v/pcresolve)](https://pypi.org/project/pcresolve/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## News

- **2026-05-28** - PCResolve 1.0.4 released: stable provenance JSON contract, `scope_model="v2"` by default, `--json` full output, expanded real-project regression baselines, and Windows-safe audit/gate tooling.

## What is PCResolve?

PCResolve is a Python project-level third-party library usage provenance analyzer. It is an explainable static analysis tool for tracing Python API call expressions to their most likely origin library.

It answers questions such as:

- Which third-party libraries does this project call?
- Which call expression belongs to `numpy`, `requests`, `flask`, `sklearn`, or another top-level library?
- How did a local symbol, return value, attribute, parameter, or container element acquire third-party provenance?
- Where is the analysis certain, and where are there multiple possible origins?

PCResolve is designed for CI pipelines, audit workflows, IDE integration, and large-scale codebase scanning. It has zero runtime third-party dependencies and supports Python 3.9+.

## Quick Start

```bash
pip install pcresolve
pcresolve /path/to/project
```

For machine-readable output:

```bash
pcresolve /path/to/project --json
```

## Usage

### CLI

```bash
pcresolve /path/to/project                         # human-readable summary
pcresolve /path/to/project --json                  # full provenance JSON
pcresolve /path/to/project --json-summary          # compact JSON summary
pcresolve /path/to/project --explain-library numpy
pcresolve /path/to/project --explain-call "np.array"
pcresolve /path/to/project --explain-symbol df
```

### Python API

```python
from pcresolve import analyze_project

result = analyze_project("/path/to/project")

for call in result.all_api_calls:
    print(call.expression, "->", call.top_library)
    print("reason:", call.reason)
    print("confidence:", call.confidence)
```

## Output

PCResolve 1.0.4 is the first stable provenance contract release. The default scope model is `v2`, and `--json` returns the full provenance schema.

The main output sections are:

| Section | Description |
|---------|-------------|
| `all_api_calls` | Every call expression with source location, resolved owner, reason, confidence, alternatives, and decorator evidence. |
| `all_symbol_provenance` | Provenance records for imports, variables, parameters, return values, attributes, container items, and decorators. |
| `library_usage` | Per-library aggregation of calls, symbols, files, reason counts, and confidence ranges. |
| `diagnostics` | Non-fatal parse, encoding, and tracing diagnostics. |

For the complete JSON contract, see [docs/output-contract.md](./docs/output-contract.md).

## Analysis Capabilities

PCResolve tracks both API call provenance and symbol provenance.

Supported patterns include:

- direct imports, aliases, wildcard imports, and re-exports;
- cross-file symbol tracing through local modules;
- function return propagation and parameter binding;
- class construction, instance attributes, and method call provenance;
- dict/list/tuple/set container items and iteration;
- decorator calls and `decorated_by` evidence;
- ambiguous flows reported through `alternatives` instead of silent guessing.

`top_library` represents the primary owner of the callable or receiver object for a call expression. Additional evidence is reported separately through fields such as `alternatives`, `decorated_by`, and symbol provenance records.

## Validation

The 1.0.4 release was validated with:

```text
pytest:          557 passed
hard baselines:  21 projects, 0 exceeded
full audit:      42 real-world projects, 0 crashes, 0 illegal keys
```

The regression gate checks that library keys stay clean, golden JSON output remains stable, and real-project baseline counts do not exceed the recorded contract.

## Limitations

PCResolve is static by design. It does not execute project code and does not model arbitrary runtime reflection, monkey patching, dynamic imports, descriptors, or full third-party library internals.

When a single origin cannot be determined confidently, PCResolve reports conservative results and preserves alternative evidence rather than choosing an unsupported library owner.

## Documentation

- [Output Contract](./docs/output-contract.md)
- [Architecture](./docs/architecture.md)
- [Trace Contract](./docs/trace-contract.md)
- [Source Semantics](./docs/source-semantics.md)
- [Real-Project Validation](./docs/real-project-validation.md)

## Development

```bash
pip install -e .
python -m pytest tests/ -v
python scripts/diff_v1_v2.py tests/fixtures/tested_projects/
python scripts/audit_tested_projects.py
```

PCResolve uses only the Python standard library at runtime. Tests use pytest.

## License

PCResolve is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
