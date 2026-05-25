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
