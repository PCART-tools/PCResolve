# PCResolve

[![PyPI](https://img.shields.io/pypi/v/pcresolve)](https://pypi.org/project/pcresolve/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Project-level Python static analysis for API ownership and library usage provenance.

## News

- **2026-05-28** - PCResolve 1.0.4 released: stable provenance JSON contract, lexical scope analysis, `--json` full output, and Windows-safe tooling.

## What is PCResolve?

PCResolve is a project-level Python static analyzer for API ownership and library usage provenance. It classifies Python API call expressions and traces the symbols that feed them to their owner: an import-backed library, Python-provided API, project-local definition, or unknown.

It answers questions such as:

- Which import-backed libraries and Python APIs does this project call?
- Which call expression belongs to `numpy`, `requests`, `json`, `pathlib`, `flask`, or another top-level library owner?
- Which calls are library-owned, Python-provided, local, or unknown?
- How did a local symbol, return value, attribute, parameter, or container element acquire library provenance?
- Where is the analysis certain, and where are there multiple possible origins?

PCResolve is designed for CI pipelines, audit workflows, IDE integration, and large-scale codebase scanning. It has zero runtime dependencies and supports Python 3.9+.

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

PCResolve 1.0.4 is the first stable provenance contract release. `--json` returns the full provenance schema.

The main output sections are:

| Section | Description |
|---------|-------------|
| `all_api_calls` | Every call expression with source location, resolved owner, reason, confidence, alternatives, and decorator evidence. |
| `all_symbol_provenance` | Provenance records for imports, variables, parameters, return values, attributes, container items, and decorators. |
| `library_usage` | Per-library aggregation of calls, symbols, files, reason counts, and confidence ranges. |
| `diagnostics` | Non-fatal parse, encoding, and tracing diagnostics. |

For the complete JSON contract, see [docs/output-contract.md](./docs/output-contract.md).

## Analysis Capabilities

PCResolve reports two connected views: API call ownership and symbol provenance.
API calls are the primary classification target. Symbol provenance explains the
imports, aliases, assignments, parameters, returns, attributes, containers, and
decorators that support each classification.

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

The current analyzer is validated against locked call-site ground truth from 42 real-world projects:

```text
ground-truth records:  5,788
primary hits:          5,539
primary recall:        0.957
false positives:       0
```

The regression gate checks complete AST call coverage, locked annotations, stable snapshots, clean library keys, and golden JSON output.

## Limitations

PCResolve is static by design. It does not execute project code and does not model arbitrary runtime reflection, monkey patching, dynamic imports, descriptors, or full library internals.

When a single origin cannot be determined confidently, PCResolve reports conservative results and preserves alternative evidence rather than choosing an unsupported library owner.

## Documentation

- [Output Contract](./docs/output-contract.md)
- [Architecture](./docs/architecture.md)
- [Trace Contract](./docs/trace-contract.md)
- [Source Semantics](./docs/source-semantics.md)
- [Real-Project Validation](./docs/real-project-validation.md)
- [Ground Truth Evaluation](./docs/ground-truth-evaluation.md)

## Development

```bash
pip install -e .
python -m pytest tests/ -v
python scripts/evaluate_ground_truth.py --view all
python scripts/verify_ground_truth_calls.py --coverage-only
python scripts/refresh_ground_truth_snapshots.py --all --check
```

PCResolve uses only the Python standard library at runtime. Tests use pytest.

## License

PCResolve is licensed under the MIT License. See [LICENSE](./LICENSE) for details.
