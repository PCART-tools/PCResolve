# PCResolve Output Contract

Ownership uses the stable `schema_version="1.0"` provenance contract and one
lexical scope model. Experimental value flow uses the separate `flow-0.2`
contract and does not change ownership output.

## CLI

```bash
pcresolve project                  # human summary
pcresolve project --json           # full provenance JSON
pcresolve project --json-summary   # compact summary JSON (CI)
pcresolve a.py                     # one file, human summary
pcresolve a.py --json              # one file, full provenance JSON
pcresolve a.py --value-flow --entry a:function
pcresolve project --explain-library numpy
pcresolve project --explain-symbol x
pcresolve project --explain-call "np.array"
pcresolve project --strict
pcresolve project --usage-summary --top 20
printf '/path/to/project\n' | pcresolve --stdin --json-summary
```

- Lexical scope analysis is the only supported scope semantics.
- `--json` is the primary machine-consumption format.
- `--json-summary` is the recommended CI format.
- Long options do not accept abbreviations. A partial option such as `--js` or
  `--json-f` exits 2 as unrecognized.
- `--strict` exits non-zero when ownership error diagnostics are present. In
  text, debug, and explain modes, the diagnostics causing that exit are shown
  even without `--verbose`. JSON modes retain diagnostics in their payload.
- Choose one output mode: full JSON (`--json`),
  `--json-summary`, `--debug-dump`, or one `--explain-*` option. Conflicting
  modes exit 2 with an argument error.
- JSON output rejects `--verbose`, `--usage-summary`, and `--quiet`.
  Explain output rejects `--usage-summary` and `--quiet`; `--debug-dump`
  rejects `--quiet`. These combinations exit 2 instead of ignoring options.
- Text diagnostics are printed once. `--verbose` also includes diagnostics
  in debug/explain output and reports `stats.skipped_modules` when diagnostics
  are present. `--quiet` suppresses the summary and filters diagnostics to
  errors, including when combined with `--verbose`. `--usage-summary` can
  include library usage in quiet mode.
- `--top N` requires a non-negative integer (default 20, `0` means unlimited).
  It limits libraries in the text and usage summaries, calls and symbols in
  explain output, and per-library `files` lists in summary JSON. Total counts
  remain unchanged. Full JSON, debug facts, diagnostics, import lists, and
  per-file statistics in explain-library output are not truncated. `--top` is
  rejected with full JSON and with a debug dump that has no appended
  `--usage-summary`, rather than being silently ignored.
- Explain queries must contain a non-whitespace name; empty queries exit 2.
- Explain queries with no matches complete successfully and report that result
  on stdout consistently for libraries, symbols, and calls.
- `--explain-call NAME` matches `func_name` or `resolved_func` by exact name
  or a dotted path suffix at a name boundary. Matching is case-sensitive and
  excludes call arguments and string contents. `Series` matches `Series`,
  `pd.Series`, and aliases resolved to `pandas.core.series.Series`; it does not
  match `ABCSeries`, `SeriesExtra`, or `Series.to_numpy`. Qualified queries
  such as `np.array`, `pandas.core.series.Series`, and `core.series.Series`
  select matching callable paths. The reported count includes all matches
  before the `--top` display limit is applied.
- Ownership and value-flow positional inputs accept a project directory or one
  existing `.py`/`.pyi` file, using relative or absolute paths. File mode reads
  only that source; it does not discover or follow sibling sources. Use
  directory mode for cross-file analysis. Value flow also accepts repeated
  `--source-file` options when an explicit multi-file source set is required.
- Missing paths, missing positional ownership input, empty stdin, and
  unsupported file inputs exit 2 as argument errors rather than producing a
  successful empty analysis.
- In file mode, the path-normalization root is the file's parent directory,
  or the directory above its outermost enclosing regular Python package
  (identified by `__init__.py` or `__init__.pyi`). This retains package module
  names, including for a selected `__init__.py`, without adding other sources.
  Ownership JSON keeps `schema_version="1.0"` and the same fields.
- `--stdin` reads one directory or source-file input path from standard input.
  It is an alternative to the positional path; using both is an error. In
  value-flow mode it also conflicts with `--source-file`, so the selected input
  source never depends on whether stdin happens to be empty.

File and directory inputs use the same ownership semantics. Given the same
analyzed source set and module mapping root, their call classifications are
the same. Missing module implementations limit both input forms: for example,
`from factory import create_app; create_app()` retains the import-backed owner
`factory` when no additional project evidence is available. The import path
alone does not prove that the module is project-local or identify a different
implementation owner.

## Python API

The stable entry points use these signatures:

```python
analyze_project(project_root)
analyze_source(source, file_path="<string>")
ProjectAnalyzer(project_root)
SingleFileAnalyzer(module_name=None, is_package=False, file_path="")
```

`analyze_project` and `ProjectAnalyzer` also accept a `.py`/`.pyi` file path,
with the same source selection and path-normalization root as the ownership
CLI. They return the existing `ProjectAnalysis` result for that single file.

`analyze_source` accepts Python source text. Its `file_path` parameter supplies
location metadata; it does not select or read a file from disk.

PCResolve uses one lexical scope model. There is no public scope-model selector
or `stats.scope_model` field.

### Experimental value-flow contract

Value-flow analysis is an additive, experimental API. It does not change the
ownership entry points or the ownership JSON schema below:

```python
FlowAnalyzer(
    source_files=None,
    import_roots=None,
    project_root=None,
    return_summaries=None,
    parameter_shapes=None,
)
FlowAnalyzer.analyze(entry, max_depth=1, max_functions=500,
                     max_call_contexts=2000)
FlowAnalyzer.expand(result, call_id, additional_depth=1)
```

Exactly one of `project_root` and `source_files` is required. `entry` is a
`FunctionRef`; its `module` and dotted `qualname` identify a function, nested
function, or method. File path and definition line can disambiguate duplicate
definitions in the Python API.

`FlowAnalysis.to_dict()` emits `schema_version="flow-0.2"` with `entry`,
`inputs`, `functions`, `calls`, and `boundaries`. `find_calls()` and
`describe_call_flow()` select exact call-site records; `trace_parameter()`
composes only the summaries already present in the snapshot. Empty flow lists
or `status="unknown"` are not no-flow proofs when boundaries remain.

The PCBench-driven extensions remain additive within `flow-0.2`:

| Location | Additive field | Meaning |
|---|---|---|
| `calls[*]` | `target_candidates` | Bounded source targets; a single `target` remains the selected static candidate when available. |
| `calls[*]` | `binding_status`, `binding_issues` | Complete/uncertain/invalid binding state and statically proven missing, duplicate, unresolved, or dynamic-expansion facts. |
| `calls[*].parameter_bindings[*]` | `destination_kind` | `parameter`, `var_positional`, `var_keyword`, or `unresolved`; variadic element positions remain in `target_path`. |
| `calls[*]` | `result_sources` | Sources of supported local container protocol results, used to relate later boundaries to input roots. |
| `functions[*]` | `mapping_effects` | Element-specific membership, pop, delete, update, and merge facts with bounded state and branch conditions. |
| `boundaries[*]` | `affected_scope`, `affected_values` | Known roots and element paths affected by the boundary, or explicit `none`/`unknown` scope. |
| source boundaries | `entry_relation`, `relation_basis`, `unaffected_values` | Static import reachability and entry parameters excluded from value impact because they are never read in the entry body; reflection suppresses exclusions. Neither is a runtime reachability proof. |

Existing fields and `schema_version="flow-0.2"` are unchanged. Consumers must
continue to treat a selected method or decorated target/class as conservative
when a corresponding override/decorator boundary is present.

The CLI selects this contract with `--value-flow` and
`--entry MODULE:QUALNAME`. In that mode, `--json` emits flow JSON rather than the
ownership schema. Commands without `--value-flow` retain the stable ownership
contract. See the [value-flow CLI and pandas example](value-flow.md) for the
complete usage and boundary semantics.

## Full provenance JSON (`--json`)

`all_api_calls` is the primary consumption surface. `all_symbol_provenance`
provides the explanation and evidence layer: it records which imports,
aliases, assignments, parameters, returns, attributes, containers, and
decorators support each call classification.

```json
{
  "schema_version": "1.0",
  "profile": "full",
  "project_root": ".",
  "stats": {},
  "diagnostics": [],
  "files": [],
  "all_api_calls": [],
  "all_symbol_provenance": [],
  "library_usage": {}
}
```

### `all_api_calls[*]` stable fields

| Field | Type | Description |
|-------|------|-------------|
| `expression` | string | Full call expression text |
| `func_name` | string | Function name without arguments |
| `parameters` | string | Argument text |
| `top_library` | string | Resolved primary owner: import-backed top-level library name, or `local`, `python`, `unknown`. PCResolve does not distinguish stdlib from PyPI: any import-backed owner keeps its top-level name (e.g. `json`, `pathlib`, `requests`, `numpy`). |
| `base_symbol` | string | Root/base symbol used for resolution |
| `reason` | string | DIRECT_IMPORT, RETURN_PROPAGATION, FLOW_MERGE, ... |
| `confidence` | float | 0.0–1.0 |
| `alternatives` | list | Alternative top libraries |
| `decorated_by` | list | Decorator library evidence |
| `file_path` | string | Relative POSIX path from project_root |
| `lineno` | int | |
| `col_offset` | int | |
| `end_lineno` | int | |
| `end_col_offset` | int | |
| `chain` | list | Trace chain |
| `resolved_func` | string | Fully qualified function path |
| `resolved_chain` | list | Resolved trace chain |

### `resolved_func` semantics

`resolved_func` attempts to qualify the called function through
its receiver's provenance. It is a best-effort display hint, not a
guaranteed precise resolution:

- **Constructor calls**: when PCResolve identifies the receiver class
  via `import_from_symbols`, `resolved_func` includes the class path
  (e.g. `requests.Session.get`, `flask.Flask.test_client`).
- **Factory returns**: when the receiver traces through a local
  function that returns an import-backed library-owned object, the class info is
  typically not preserved.  PCResolve may produce a library-level
  function (e.g. `requests.get`) when the call path normalizes;
  otherwise the original receiver expression is preserved while
  `top_library` carries the ownership.
- **Local / unknown**: stays as the original expression or `local`.
- **Zero-argument `super()` methods**: for a statically known direct single
  external base, the hint uses the base's import path and method name
  (e.g. `tensorflow.keras.layers.Layer.get_config`). Unsupported or ambiguous
  inheritance and explicit `super(...)` retain the original function name.
  This does not identify the method's internal defining class.
  Class decorators remain conservative, with a narrow exception for an
  import-backed `tensorflow.keras.utils.register_keras_serializable(...)`
  call using literal `package`/`name` configuration on a module-level class.
  This requires a direct named import (including a symbol alias); wildcard
  imports, visible rebinding, and module-attribute decorator calls remain
  unsupported.
  Its [registration implementation](https://github.com/tensorflow/tensorflow/blob/v2.10.0/tensorflow/python/keras/utils/generic_utils.py)
  returns the original class; unknown or ambiguous decorators still prevent
  expansion, including when stacked with this registration decorator.
- `resolved_func` must not be treated as an importable symbol; it
  may not exist at that path in the library.

`resolved_chain` is `[func_name, resolved_func, top_library]`.

## Summary JSON (`--json-summary`)

```json
{
  "schema_version": "1.0",
  "profile": "summary",
  "project_root": ".",
  "stats": {},
  "diagnostics": [],
  "libraries": {}
}
```

Summary excludes `all_api_calls`, `all_symbol_provenance`,
and per-file `symbols`/`chains`.

## Path normalization

All paths use POSIX separators (`/`) relative to `project_root`.
External paths use the `<external>/...` prefix.

## Reason constants

| Reason | Meaning |
|--------|---------|
| DIRECT_IMPORT | Call traced directly to an import alias or from-import |
| TRANSITIVE_IMPORT | Call traced through a re-export or transitive module chain |
| LOCAL_DEFINITION | Call is a locally defined function, method, or class |
| BUILTIN | Call is a Python builtin (no import required) |
| PARAMETER_PROPAGATION | Source traced through a function parameter |
| RETURN_PROPAGATION | Source traced through a function return value |
| FLOW_MERGE | Multiple branches/sources merged (if/else, multi-return, SourceSet) |
| UNRESOLVED | Trace could not reach a terminal origin |

`PARAMETER_PROPAGATION` remains a stable reason value. Parameter evidence often
resolves before final classification, so the resulting call may instead report
`RETURN_PROPAGATION`, `FLOW_MERGE`, or `TRANSITIVE_IMPORT`.

## Confidence rules

| Reason | Confidence |
|--------|-----------|
| DIRECT_IMPORT | 1.0 |
| LOCAL_DEFINITION | 1.0 |
| BUILTIN | 1.0 |
| PARAMETER_PROPAGATION | 0.9 |
| RETURN_PROPAGATION | 0.9 |
| TRANSITIVE_IMPORT | 0.9 |
| FLOW_MERGE (single) | 0.85 |
| FLOW_MERGE (N alts) | max(1/N, 0.2) |
| FLOW_MERGE with a conservative local primary | 0.5 |
| UNRESOLVED | 0.0 |
