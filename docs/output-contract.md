# PCResolve Output Contract

## Output Profiles

| Profile | Flag | Audience | Stability | Volume |
|---------|------|----------|-----------|--------|
| `summary` | `--json-summary` | CI, scripts, dashboards | **Stable public contract** | Small |
| `full` | `--json-full` / `--json-stable` | Debugging, golden regression | Additive internal contract | Large |
| `legacy` | `--json` | Backward compatibility | Compatibility mode | Large |
| `explain` | `--explain-library/symbol/call` | Human troubleshooting | Text format, not parse-stable | Small |

## Schema Version

- `schema_version` is `"1.0"` for all profiles.
- Adding optional fields does not increment the version.
- Removing, renaming, or changing field types/semantics requires a version bump.
- Breaking changes to the summary profile must be documented.

## Path Convention

- All paths in `summary`, `full`, and `json-stable` are relative POSIX.
- Paths outside `project_root` use `<external>/...` prefix.
- Windows `\` is normalised to `/`.

## Sort Order

| Field | Sort |
|-------|------|
| Libraries | Library name, ascending |
| Files | Relative path, ascending |
| API calls | File path, line, column, expression |
| Symbol provenance | File path, line, column, symbol, kind |
| Diagnostics | File path, line, column |

## Null / Empty Convention

- No diagnostics: `[]`
- No library usage: `{}`
- No evidence confidence: `0.0` / `0.0`

## Summary Profile Fields

```json
{
  "schema_version": "1.0",
  "profile": "summary",
  "project_root": ".",
  "stats": {
    "total_modules": 12,
    "parsed_modules": 12,
    "skipped_modules": 0,
    "scope_model": "v1",
    "api_call_count": 84,
    "library_count": 5,
    "diagnostic_error_count": 0,
    "diagnostic_warning_count": 0
  },
  "diagnostics": [],
  "libraries": {
    "requests": {
      "api_call_count": 18,
      "symbol_count": 6,
      "file_count": 3,
      "files": ["api/client.py", "services/http.py"],
      "imports": ["requests"],
      "kind_counts": {"import": 1, "variable": 4},
      "min_confidence": 1.0,
      "max_confidence": 1.0
    }
  }
}
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Analysis complete, no blocking issues |
| 1 | CLI argument error, path error, or `--strict` with error diagnostics |
| 2 | (Reserved) Internal analyser exception |
| 3 | (Reserved) Policy gate failure |

## ApiCall Fields (Full Profile)

All fields are present in the `full` profile.  Summary profile includes only
`top_library` and `reason_counts` aggregated per library.

| Field | Type | Default | Stability | Added |
|-------|------|---------|-----------|-------|
| `expression` | string | — | Stable | — |
| `top_library` | string | — | Stable | — |
| `base_symbol` | string | — | Stable | — |
| `chain` | list | — | Stable | — |
| `file_path` | string | `""` | Stable | — |
| `lineno` | int | `0` | Stable | — |
| `col_offset` | int | `0` | Stable | — |
| `end_lineno` | int | `0` | Stable | — |
| `end_col_offset` | int | `0` | Stable | — |
| `func_name` | string | `""` | Stable | — |
| `parameters` | string | `""` | Stable | — |
| `resolved_func` | string | `""` | Stable | — |
| `resolved_chain` | list | `[]` | Stable | — |
| `reason` | string | `""` | Stable | Phase 8A |
| `confidence` | float | `1.0` | Stable | Phase 8A |
| `alternatives` | list | `[]` | Stable | Phase 8A |
| `decorated_by` | list | `[]` | Additive | Phase 8C+ |

### `ApiCall.decorated_by` Field Contract

- **Type**: `list[str]`, default `[]`
- **Stability**: additive-only within a schema version.  New decorator evidence
  may appear; existing library entries are never removed without a version bump.
- **Null/empty**: `[]` means "no decorator evidence found on this call".
  May be a false negative for method calls (`obj.method()`) until Phase 7B.
- **Values**: only import-backed library names.
  `"local"`, `"python"`, `"unknown"` are excluded.
- **Matching**: exact match on `(file_path, func_name)` where `func_name`
  is the API call's bare function name (e.g. `"index"` for `index()`).
  Method calls (`c.method()`) currently return `[]` — class resolution
  needed for reliable scope-aware matching (Phase 7B).
- **Existing values are not removed** when a schema version bumps;
  they may be augmented with new library names as analysis improves.

### SymbolProvenance `kind="decorated_by"`

SymbolProvenance records with `kind="decorated_by"` carry:

| Field | Value |
|-------|-------|
| `symbol` | Decorated function/class name |
| `kind` | `"decorated_by"` |
| `top_library` | Library providing the decorator (or `"local"`) |
| `scope_name` | Class name for methods, empty for module-level functions |
| `chain` | Trace chain from decorator expression to library |
