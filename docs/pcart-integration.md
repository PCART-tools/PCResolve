# PCART 1.0.4 Integration Guide

PCART consumes PCResolve's provenance output to detect API
compatibility issues for a given third-party library.

## Consumption rules

```
确定纳入 (direct):
  call.top_library == target_library

候选纳入 (candidate):
  target_library in call.alternatives
  target_library in call.decorated_by

排除 (exclude):
  call.top_library in (local, python, unknown)
  AND target_library not in alternatives
  AND target_library not in decorated_by
```

PCART should use `reason` and `confidence` to decide whether
to run a full compatibility check or mark the call as a
candidate, but must not rely on `top_library` alone — that
would miss multi-source returns and decorator-transformed
local targets.

## JSON format

Consume `--json` (full provenance):

```bash
pcresolve /path/to/project --json
```

Key fields:

- `all_api_calls[*].top_library` — primary library
- `all_api_calls[*].alternatives` — other candidates
- `all_api_calls[*].decorated_by` — decorator evidence
- `all_api_calls[*].reason` — classification reason
- `all_api_calls[*].confidence` — 0.0–1.0
- `all_api_calls[*].file_path` — relative POSIX path
- `all_api_calls[*].lineno` / `col_offset`

For library-level aggregation use `library_usage`.

## Example

```python
import json, subprocess

result = json.loads(
    subprocess.check_output(["pcresolve", "/path/to/project", "--json"])
)

target = "numpy"
for call in result["all_api_calls"]:
    if call["top_library"] == target:
        check_api_compatibility(call)           # direct
    elif target in (call.get("alternatives") or []):
        mark_candidate(call, "alternative")     # candidate
    elif target in (call.get("decorated_by") or []):
        mark_candidate(call, "decorator")       # candidate
```
