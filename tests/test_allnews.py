## @package tests.test_allnews
#  Test pcresolve against the allnews project oracle.
#
#  allnews is an Armenian NLP pipeline with 9 Python files.
#  It uses: gensim, keras, nltk, numpy, pandas, sklearn, pymysql.
#
#  Oracle built by manual code review of all 9 source files.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "allnews"
)


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


@pytest.fixture(scope="module")
def calls_by_top(result):
    d = {}
    for f in result.files:
        for c in f.api_calls:
            d.setdefault(c.top_library, []).append(c)
    return d


# ── Structural checks ──────────────────────────────────────────────────

def test_all_files_analyzed(result):
    assert len(result.files) == 9, (
        f"Expected 9 files, got {len(result.files)}"
    )


def test_all_files_have_module_name(result):
    for f in result.files:
        assert f.module_name, (
            f"{os.path.basename(f.file_path)} has no module_name"
        )


# ── Correct third-party classification ─────────────────────────────────

def test_gensim_calls(calls_by_top):
    assert "gensim" in calls_by_top, "No gensim calls found"
    gensim_exprs = [c.expression for c in calls_by_top["gensim"]]
    assert any("FastText" in e for e in gensim_exprs)


def test_keras_calls(calls_by_top):
    assert "keras" in calls_by_top
    assert len(calls_by_top["keras"]) >= 15


def test_nltk_calls(calls_by_top):
    assert "nltk" in calls_by_top


def test_sklearn_calls(calls_by_top):
    assert "sklearn" in calls_by_top


def test_pymysql_calls(calls_by_top):
    assert "pymysql" in calls_by_top


# ── Local function classification ──────────────────────────────────────

def test_local_classes_are_local(calls_by_top):
    """Locally defined classes should be classified as local."""
    local_exprs = [c.expression for c in calls_by_top.get("local", [])]
    indicators = [
        "MySQL(", "ConllReader(", "Tokenizer(", "Dictionary(",
        "NextFile(", "OutputSplitter(", "Extractor(", "Template(",
    ]
    found = sum(1 for e in local_exprs for ind in indicators if ind in e)
    assert found > 0, "Expected local class instantiations classified as local"


# ── Stdlib modules (need import → correctly third-party) ──────────────

def test_stdlib_modules_are_third_party(calls_by_top):
    """Stdlib modules that need import are correctly third-party top_library."""
    for m in ["re", "argparse", "logging", "os", "multiprocessing", "io",
              "fileinput", "timeit", "time", "types", "gzip", "json",
              "urllib", "itertools", "bz2", "codecs", "cgi", "xml"]:
        assert m in calls_by_top, (
            f"{m} should appear as top_library (stdlib, needs import)"
        )

# ── Known issues — documented limitations ──────────────────────────────


@pytest.mark.xfail(reason="KNOWN: self(5) + call_result leaks (get_url/clean/compact: 3 calls)")
def test_local_variables_not_top(calls_by_top):
    local_vars = ["self", "get_url", "clean", "compact"]
    leaked = [v for v in local_vars if v in calls_by_top]
    assert not leaked, f"Local variables leaked: {leaked}"


def test_local_modules_not_top(calls_by_top):
    leaked = [m for m in ["allnews_am", "allnews_am.processing"]
              if m in calls_by_top]
    assert not leaked, f"Local modules leaked: {leaked}"


def test_builtins_not_top(calls_by_top):
    builtin_leaks = [b for b in ["unichr", "xrange"] if b in calls_by_top]
    assert not builtin_leaks, f"Builtin names leaked: {builtin_leaks}"


def test_no_structured_tuples(calls_by_top):
    structured = [k for k in calls_by_top if isinstance(k, tuple) or str(k).startswith("(")]
    assert not structured, f"Structured tuples leaked: {structured}"
