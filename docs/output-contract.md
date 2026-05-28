# PCResolve 1.0.4 Output Contract

PCResolve 1.0.4 is the first stable provenance contract release.
JSON outputs before 1.0.4 are experimental and not guaranteed
compatible.

## CLI

```bash
pcresolve project                  # human summary (v2 default)
pcresolve project --json           # full provenance JSON
pcresolve project --json-summary   # compact summary JSON (CI)
pcresolve project --explain-library numpy
pcresolve project --explain-symbol x
pcresolve project --explain-call "np.array"
```

- `scope_model` defaults to `v2` (lexical scopes).
- `--scope-model v1` is still accepted for legacy compatibility.
- `--json` is the primary machine-consumption format.
- `--json-full` and `--json-stable` are hidden aliases for `--json`.
- `--json-summary` is the recommended CI format.

## Full provenance JSON (`--json`)

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
| `top_library` | string | Resolved top-level library |
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
| UNRESOLVED | 0.0 |

## Breaking changes (1.0.4)

- Default `scope_model`: `v1` → `v2`.
- `--json`: legacy dataclass dump → full provenance schema.
- `--json-stable`: deprecated, hidden.
- Pre-1.0.4 JSON: experimental, no compatibility guarantee.
