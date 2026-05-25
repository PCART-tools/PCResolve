## @package tests.test_golden_output
#  Golden output tests: compare current JSON output against recorded baselines.
#
#  When a behavioural change is expected (e.g. accuracy improvement),
#  update the golden file and explain the change in the commit message.

import json
import os
import subprocess
import sys

GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))


def _run_analyze(fixture_rel):
    """Run pcresolve --json-stable on a fixture and return parsed JSON."""
    fixture_path = os.path.join(PROJECT_DIR, fixture_rel)
    result = subprocess.run(
        [sys.executable, "-m", "pcresolve", "--json-stable", fixture_path],
        capture_output=True, text=True, cwd=PROJECT_DIR,
    )
    assert result.returncode == 0, f"pcresolve failed: {result.stderr}"
    return json.loads(result.stdout)


def _load_golden(name):
    """Load a golden JSON file."""
    path = os.path.join(GOLDEN_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_calls(calls):
    """Extract stable key fields from a list of API call dicts for comparison."""
    keys = ("expression", "top_library", "base_symbol", "chain",
            "file_path", "lineno", "col_offset", "func_name", "resolved_func")
    result = []
    for c in calls:
        record = {k: c.get(k) for k in keys}
        result.append(record)
    result.sort(key=lambda r: (r["file_path"], r["lineno"], r["col_offset"], r["expression"]))
    return result


def _normalize_symbols(files):
    """Extract stable per-file symbols/chains for comparison."""
    result = {}
    for f in files:
        result[f["file_path"]] = {
            "module_name": f.get("module_name"),
            "symbols": dict(sorted(f.get("symbols", {}).items())),
            "chains": {k: v for k, v in sorted(f.get("chains", {}).items())},
        }
    return result


# ── golden fixtures ──────────────────────────────────────────────────────


def test_golden_tests2():
    """Cross-file return/source behaviour."""
    current = _run_analyze("tests/fixtures/tests2/")
    golden = _load_golden("tests2.json")

    assert current["schema_version"] == golden["schema_version"]
    assert len(current["files"]) == len(golden["files"])

    current_calls = _normalize_calls(current["all_api_calls"])
    golden_calls = _normalize_calls(golden["all_api_calls"])
    assert current_calls == golden_calls, "API calls differ from golden"

    current_sym = _normalize_symbols(current["files"])
    golden_sym = _normalize_symbols(golden["files"])
    assert current_sym == golden_sym, "Symbols/chains differ from golden"


def test_golden_api_classification():
    """Local vs third-party classification boundary."""
    current = _run_analyze("tests/fixtures/api_classification/")
    golden = _load_golden("api_classification.json")

    assert current["schema_version"] == golden["schema_version"]
    assert len(current["files"]) == len(golden["files"])

    current_calls = _normalize_calls(current["all_api_calls"])
    golden_calls = _normalize_calls(golden["all_api_calls"])
    assert current_calls == golden_calls, "API calls differ from golden"

    current_sym = _normalize_symbols(current["files"])
    golden_sym = _normalize_symbols(golden["files"])
    assert current_sym == golden_sym, "Symbols/chains differ from golden"


def test_golden_wildcard_re_export():
    """Wildcard/re-export historical compatibility."""
    current = _run_analyze("tests/fixtures/test_wildcard_re_export/")
    golden = _load_golden("test_wildcard_re_export.json")

    assert current["schema_version"] == golden["schema_version"]
    assert len(current["files"]) == len(golden["files"])

    current_calls = _normalize_calls(current["all_api_calls"])
    golden_calls = _normalize_calls(golden["all_api_calls"])
    assert current_calls == golden_calls, "API calls differ from golden"

    current_sym = _normalize_symbols(current["files"])
    golden_sym = _normalize_symbols(golden["files"])
    assert current_sym == golden_sym, "Symbols/chains differ from golden"
