## @package tests.test_diagnostics
#  Tests for structured diagnostics and error recovery.

import json
import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
BAD_FIXTURE = os.path.join(PROJECT_DIR, "tests", "fixtures", "regression_parse_errors")
TESTS2_FIXTURE = os.path.join(PROJECT_DIR, "tests", "fixtures", "tests2")


def _run(*args):
    """Run pcresolve and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "pcresolve"] + list(args),
        capture_output=True, text=True, cwd=PROJECT_DIR,
    )
    return result.returncode, result.stdout, result.stderr


# ── non-strict mode ─────────────────────────────────────────────────────


def test_syntax_error_does_not_crash_default_mode():
    """Broken .py file should be skipped, not crash analysis."""
    rc, stdout, stderr = _run(BAD_FIXTURE)
    assert rc == 0, "Default mode should exit 0"


def test_syntax_error_is_reported_in_json():
    """JSON output should contain diagnostics for bad files."""
    rc, stdout, stderr = _run("--json", BAD_FIXTURE)
    assert rc == 0
    data = json.loads(stdout)
    assert "diagnostics" in data
    diags = data["diagnostics"]
    assert len(diags) >= 1
    assert any(d["code"] == "SYNTAX_ERROR" for d in diags)


def test_syntax_error_json_stable():
    """Stable JSON should also contain diagnostics."""
    rc, stdout, stderr = _run("--json-stable", BAD_FIXTURE)
    assert rc == 0
    data = json.loads(stdout)
    assert "diagnostics" in data
    assert len(data["diagnostics"]) >= 1
    assert any(d["code"] == "SYNTAX_ERROR" for d in data["diagnostics"])


def test_non_strict_mode_skips_bad_file():
    """Bad file should be skipped, no FileAnalysis produced for it."""
    rc, stdout, stderr = _run("--json", BAD_FIXTURE)
    data = json.loads(stdout)
    assert data.get("stats", {}).get("skipped_modules", 0) >= 1


# ── strict mode ─────────────────────────────────────────────────────────


def test_strict_mode_fails_on_syntax_error():
    """--strict with a syntax error file should exit non-zero."""
    rc, stdout, stderr = _run("--strict", "--json", BAD_FIXTURE)
    assert rc != 0, "Strict mode should fail on syntax error"


def test_strict_mode_passes_on_clean_project():
    """--strict with a clean project should exit 0."""
    clean = os.path.join(PROJECT_DIR, "tests", "fixtures", "tests2")
    rc, stdout, stderr = _run("--strict", "--json", clean)
    assert rc == 0, "Strict mode should pass on clean project"


# ── verbose ─────────────────────────────────────────────────────────────


def test_verbose_prints_diagnostics():
    """--verbose should print diagnostic summary in text mode."""
    rc, stdout, stderr = _run("--verbose", BAD_FIXTURE)
    assert rc == 0
    assert "SYNTAX_ERROR" in stdout


# ── project-level analysis ──────────────────────────────────────────────


def test_project_with_mixed_good_and_bad_files(tmp_path):
    """Project with both good and bad files should analyze the good ones."""
    (tmp_path / "good.py").write_text("import os\nos.getcwd()")
    (tmp_path / "bad.py").write_text("def broken(:\n    pass")
    rc, stdout, stderr = _run("--json", str(tmp_path))
    assert rc == 0
    data = json.loads(stdout)
    assert len(data["files"]) >= 1  # good.py was analyzed
    assert data["stats"]["skipped_modules"] >= 1  # bad.py was skipped
    assert any(d["code"] == "SYNTAX_ERROR" for d in data["diagnostics"])


# ── explain-library CLI ─────────────────────────────────────────────────


def test_explain_library_shows_files():
    """--explain-library output must include per-file call/symbol counts."""
    _, stdout, _ = _run("--explain-library", "requests", TESTS2_FIXTURE)
    assert "Files" in stdout
    assert "calls" in stdout
    assert "symbols" in stdout


def test_explain_library_shows_api_calls():
    """--explain-library output must include API call expressions."""
    _, stdout, _ = _run("--explain-library", "numpy", TESTS2_FIXTURE)
    assert "Top API calls" in stdout or "numpy" in stdout.lower()


# ── quiet mode ──────────────────────────────────────────────────────────


def test_quiet_shows_diagnostics_on_error():
    """--quiet must still print error diagnostics when present."""
    _, stdout, _ = _run("--quiet", BAD_FIXTURE)
    assert "SYNTAX_ERROR" in stdout or "SyntaxError" in stdout or "error" in stdout.lower()
