## @package tests.test_golden_output
#  Golden output tests: compare current JSON output against recorded baselines.
#
#  When a behavioural change is expected (e.g. accuracy improvement),
#  update the golden file and explain the change in the commit message.

import json
import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
GOLDEN_DIR = os.path.join(os.path.dirname(__file__), "golden")


def _run(pcresolve_args):
    """Run pcresolve with given args and return parsed JSON."""
    result = subprocess.run(
        [sys.executable, "-m", "pcresolve"] + pcresolve_args,
        capture_output=True, text=True, cwd=PROJECT_DIR,
    )
    assert result.returncode == 0, f"pcresolve failed: {result.stderr}"
    return json.loads(result.stdout)


def _load_golden(name):
    """Load a golden JSON file from tests/golden/."""
    path = os.path.join(GOLDEN_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── normalisers ──────────────────────────────────────────────────────────

def _normalize_calls(calls):
    keys = ("expression", "top_library", "base_symbol", "chain",
            "file_path", "lineno", "col_offset", "func_name", "resolved_func")
    result = []
    for c in calls:
        result.append({k: c.get(k) for k in keys})
    result.sort(key=lambda r: (r["file_path"], r["lineno"], r["col_offset"], r["expression"]))
    return result


def _normalize_symbols(files):
    result = {}
    for f in files:
        result[f["file_path"]] = {
            "module_name": f.get("module_name"),
            "symbols": dict(sorted(f.get("symbols", {}).items())),
            "chains": {k: v for k, v in sorted(f.get("chains", {}).items())},
        }
    return result


def _normalize_provenance(provenance):
    keys = ("symbol", "kind", "top_library", "chain",
            "scope_name", "file_path", "lineno", "col_offset")
    result = []
    for p in provenance:
        result.append({k: p.get(k) for k in keys})
    result.sort(key=lambda r: (r["file_path"], r["lineno"], r["col_offset"], r["symbol"]))
    return result


def _normalize_library_usage(usage):
    result = {}
    for lib, u in sorted(usage.items()):
        result[lib] = {
            "api_call_count": u.get("api_call_count", 0),
            "symbol_count": u.get("symbol_count", 0),
            "files": sorted(u.get("files", [])),
            "imports": sorted(u.get("imports", [])),
        }
    return result


def _normalize_diagnostics(diags):
    keys = ("code", "message", "severity", "file_path", "lineno")
    return sorted([{k: d.get(k) for k in keys} for d in diags],
                  key=lambda r: (r["file_path"], r["lineno"]))


# ── full profile golden ─────────────────────────────────────────────────

def _golden_full(current, golden):
    assert current["profile"] == "full"
    assert current["schema_version"] == golden["schema_version"]
    assert len(current["files"]) == len(golden["files"])

    cur = _normalize_calls(current["all_api_calls"])
    gold = _normalize_calls(golden["all_api_calls"])
    assert cur == gold, "API calls differ"

    cur = _normalize_symbols(current["files"])
    gold = _normalize_symbols(golden["files"])
    assert cur == gold, "Symbols/chains differ"

    cur = _normalize_provenance(current.get("all_symbol_provenance", []))
    gold = _normalize_provenance(golden.get("all_symbol_provenance", []))
    assert cur == gold, "Provenance differs"

    cur = _normalize_library_usage(current.get("library_usage", {}))
    gold = _normalize_library_usage(golden.get("library_usage", {}))
    assert cur == gold, "Library usage differs"

    cur = _normalize_diagnostics(current.get("diagnostics", []))
    gold = _normalize_diagnostics(golden.get("diagnostics", []))
    assert cur == gold, "Diagnostics differ"

    assert current.get("stats", {}) == golden.get("stats", {}), "Stats differ"


def test_full_tests2():
    _golden_full(_run(["--json-full", "tests/fixtures/tests2/"]),
                 _load_golden("full/tests2.json"))


def test_full_api_classification():
    _golden_full(_run(["--json-full", "tests/fixtures/api_classification/"]),
                 _load_golden("full/api_classification.json"))


def test_full_wildcard_re_export():
    _golden_full(_run(["--json-full", "tests/fixtures/test_wildcard_re_export/"]),
                 _load_golden("full/test_wildcard_re_export.json"))


# ── summary profile golden ──────────────────────────────────────────────

def _golden_summary(current, golden):
    assert current["profile"] == "summary"
    assert current["schema_version"] == golden["schema_version"]
    assert current["libraries"] == golden["libraries"]
    assert current["stats"] == golden["stats"]
    cur = _normalize_diagnostics(current.get("diagnostics", []))
    gold = _normalize_diagnostics(golden.get("diagnostics", []))
    assert cur == gold, "Diagnostics differ"


def test_summary_tests2():
    _golden_summary(_run(["--json-summary", "tests/fixtures/tests2/"]),
                    _load_golden("summary/tests2.json"))


def test_summary_api_classification():
    _golden_summary(_run(["--json-summary", "tests/fixtures/api_classification/"]),
                    _load_golden("summary/api_classification.json"))


def test_summary_wildcard_re_export():
    _golden_summary(_run(["--json-summary", "tests/fixtures/test_wildcard_re_export/"]),
                    _load_golden("summary/test_wildcard_re_export.json"))


# ── alias tests ─────────────────────────────────────────────────────────

def test_json_stable_aliases_json_full():
    """--json-stable produces same output as --json-full."""
    full = _run(["--json-full", "tests/fixtures/tests2/"])
    stable = _run(["--json-stable", "tests/fixtures/tests2/"])
    assert full == stable, "--json-stable must equal --json-full"


def test_full_profile_includes_decorated_by():
    """A decorated local call must include decorated_by in full JSON output."""
    code = ("import flask\n"
            "app = flask.Flask(__name__)\n"
            "@app.route('/')\n"
            "def index():\n"
            "    return 'hello'\n"
            "index()\n")
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "main.py"), "w") as f:
            f.write(code)
        r = subprocess.run(
            [sys.executable, "-m", "pcresolve", td, "--json-full"],
            capture_output=True, text=True)
        data = json.loads(r.stdout)
        index_calls = [c for c in data.get("all_api_calls", [])
                       if c.get("expression") == "index()"]
        assert len(index_calls) == 1, f"Expected 1 index() call, got {index_calls}"
        call = index_calls[0]
        assert call["top_library"] == "local", \
            f"index() should be local, got {call['top_library']}"
        assert "flask" in call.get("decorated_by", []), \
            f"index().decorated_by should contain flask, got {call.get('decorated_by')}"


def test_json_summary_excludes_full_facts():
    """Summary must not include all_api_calls or all_symbol_provenance."""
    summary = _run(["--json-summary", "tests/fixtures/tests2/"])
    assert "all_api_calls" not in summary
    assert "all_symbol_provenance" not in summary
