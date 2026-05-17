## @package tests.test_final
#  Test pcresolve against the final (honeybee ML) project oracle.
#
#  final is a bee colony loss analysis pipeline (5 files).
#  It uses: sklearn, matplotlib, pandas, scipy, seaborn.
#
#  Oracle built by code review of all source files.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "final"
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

def test_all_files_analyzed(result):
    assert len(result.files) == 5


# ── Correct third-party classifications ─────────────────────────────────

def test_sklearn_calls(calls_by_top):
    assert "sklearn" in calls_by_top
    assert len(calls_by_top["sklearn"]) >= 100

def test_matplotlib_calls(calls_by_top):
    assert "matplotlib" in calls_by_top

def test_pandas_calls(calls_by_top):
    assert "pandas" in calls_by_top

def test_seaborn_calls(calls_by_top):
    assert "seaborn" in calls_by_top

def test_scipy_stats_is_third_party(calls_by_top):
    """scipy.stats needs import - correctly third-party."""
    assert "scipy" in calls_by_top


# ── Known issues ───────────────────────────────────────────────────────

@pytest.mark.xfail(reason="KNOWN: model local var leak (1) + model() call_result (1)")
def test_local_vars_not_top(calls_by_top):
    leaked = [v for v in ["model", "model()"] if v in calls_by_top]
    assert not leaked, f"Local vars/call_result leaked: {leaked}"
