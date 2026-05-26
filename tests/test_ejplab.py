## @package tests.test_ejplab
#  Test pcresolve against the EJPLab project oracle.
#
#  EJPLab is a protein embedding extraction script (1 file).
#  It uses: matplotlib, polars, torch, seaborn, datasets, numpy, pandas.
#
#  Oracle built by code review of the single source file.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "EJPLab"
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


# ── Structural ─────────────────────────────────────────────────────────

def test_one_file_analyzed(result):
    assert len(result.files) == 1
    assert result.files[0].module_name is not None


# ── Correct third-party classifications ─────────────────────────────────

def test_matplotlib_calls(calls_by_top):
    assert "matplotlib" in calls_by_top

def test_polars_calls(calls_by_top):
    assert "polars" in calls_by_top

def test_torch_calls(calls_by_top):
    assert "torch" in calls_by_top

def test_seaborn_calls(calls_by_top):
    assert "seaborn" in calls_by_top

def test_datasets_calls(calls_by_top):
    assert "datasets" in calls_by_top

def test_numpy_calls(calls_by_top):
    assert "numpy" in calls_by_top

def test_pandas_calls(calls_by_top):
    assert "pandas" in calls_by_top


# ── Known issues ───────────────────────────────────────────────────────

def test_big_df_not_top(calls_by_top):
    assert "big_df" not in calls_by_top

def test_no_structured_tuples(calls_by_top):
    structured = [k for k in calls_by_top if str(k).startswith("(")]
    assert not structured, f"Unresolved: {structured}"

def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["tokenizer", "process_batch()"] if v in calls_by_top]
    assert not leaked, f"Local vars leaked: {leaked}"
