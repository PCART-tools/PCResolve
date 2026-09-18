# PCResolve

[![PyPI](https://img.shields.io/pypi/v/pcresolve)](https://pypi.org/project/pcresolve/) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)

Project-level Python static analysis for API ownership and library usage provenance.

## News

- **2026-09-17** - PCResolve 1.0.6 adds experimental interprocedural value-flow
  analysis for parameters, receivers, returns, and mutation effects, backed by
  a shared program-facts layer and a 472-check evaluation matrix.
- **2026-09-03** - PCResolve 1.0.5 standardizes on lexical scope analysis and
  expands context-sensitive parameter, return, call, and receiver provenance.
- **2026-05-28** - PCResolve 1.0.4 released: stable provenance JSON contract, `scope_model="v2"` by default, `--json` full output, expanded real-project regression baselines, and Windows-safe audit/gate tooling.

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

To analyze just one Python source file:

```bash
pcresolve a.py
pcresolve a.py --json
```

Ownership analysis accepts relative or absolute `.py` and `.pyi` paths. File
mode analyzes only the selected file. Use a project directory when provenance
needs to be traced across local imports. Both inputs use the same ownership
rules; with the same source set and module mapping root, call classifications
are the same.

To analyze explicit parameter and return dependencies from one entry function:

```bash
pcresolve /path/to/project --value-flow --entry package.module:function --depth 2 --json
```

For explicit files in value-flow mode, use `--source-file`; its positional
input remains a project directory.

## Usage

### CLI

```bash
pcresolve /path/to/project                         # human-readable summary
pcresolve /path/to/project --json                  # full provenance JSON
pcresolve /path/to/project --json-summary          # compact JSON summary
pcresolve /path/to/a.py --json                     # one file, full provenance JSON
pcresolve /path/to/project --explain-library numpy
pcresolve /path/to/project --explain-call "np.array"
pcresolve /path/to/project --explain-symbol df
```

`--explain-call NAME` matches a callable's name or resolved path, using exact
names or dotted path suffixes. For example, `Series` selects `Series(...)`,
`pd.Series(...)`, and aliases whose resolved path ends in `.Series`. Arguments,
string contents, partial names such as `ABCSeries`, and methods such as
`Series.to_numpy(...)` do not match that query. Matching is case-sensitive.

Choose one output mode: `--json`, `--json-summary`, `--debug-dump`, or one
`--explain-*` option. Conflicting modes and empty explain queries are CLI
errors. JSON output rejects the text controls `--verbose`, `--quiet`, and
`--usage-summary`. Explain output accepts `--verbose` to include diagnostics;
`--quiet` and `--usage-summary` are summary controls. `--debug-dump` also
rejects `--quiet`.

`--top N` requires a non-negative integer; `0` means unlimited. It limits
libraries in text and usage summaries, calls and symbols in explain output,
and per-library file details in summary JSON. Counts always cover the complete
analysis. Full JSON and the debug dump retain all facts. Diagnostics appear
once; `--quiet --verbose` shows only error diagnostics and the skipped-file
count when diagnostics are present.

### Python API

```python
from pcresolve import analyze_project

result = analyze_project("/path/to/project")
# Or select one source file: result = analyze_project("a.py")

for call in result.all_api_calls:
    print(call.expression, "->", call.top_library)
    print("reason:", call.reason)
    print("confidence:", call.confidence)
```

Experimental value flow uses a separate result contract:

```python
from pcresolve import FlowAnalyzer, FunctionRef

analyzer = FlowAnalyzer(project_root="/path/to/project")
flow = analyzer.analyze(
    FunctionRef(module="package.module", qualname="ClassName.method"),
    max_depth=2,
)
```

## Output

PCResolve 1.0.4 is the first stable provenance contract release. In ownership
mode, `--json` returns the full provenance schema. With `--value-flow`, it
returns the separate experimental `flow-0.2` schema.

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

The experimental `FlowAnalyzer` answers a separate dependency question. It
records actual-to-formal argument bindings, entry-parameter flows into calls,
receiver flows, supported mutations and effects, and call-result flows into
caller returns. Missing paths are reported as unknown when analysis boundaries
remain; they are not proofs that no runtime flow exists.

## Validation

The current analyzer is validated against locked call-site ground truth from 42 real-world projects:

```text
ground-truth records:  5,788
primary hits:          5,548
primary misses:          240
primary recall:        0.959
false positives:       0
```

The regression gate checks complete AST call coverage, locked annotations, stable snapshots, clean library keys, and golden JSON output.

The separate value-flow development matrix covers 83 entry functions and 472
binding, call, parameter, receiver, return, and boundary checks. All currently
match their reviewed expectations. This is a regression matrix used to guide
implementation, not a held-out estimate of real-project accuracy.

## Limitations

PCResolve is static by design. It does not execute project code and does not model arbitrary runtime reflection, monkey patching, dynamic imports, descriptors, or full library internals.

When a single origin cannot be determined confidently, PCResolve reports conservative results and preserves alternative evidence rather than choosing an unsupported library owner.

Value-flow expansion is bounded by the selected source files, call depth,
summary budget, and call-site budget. Dynamic dispatch, general heap behavior,
external implementations, and unsupported Python constructs remain explicit
boundaries.

## Documentation

- [Experimental Value Flow API and pandas Example](./docs/value-flow.md)
- [Value Flow Evaluation Matrix and Tests](./docs/value-flow-testing.md)
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
