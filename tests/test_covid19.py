## @package tests.test_covid19
#  Test pcresolve against the covid19 project oracle.
#
#  covid19 is a COVID-19 data analysis script (1 file).
#  It uses: pandas, matplotlib, numpy, sklearn, datetime.
#
#  Oracle built by code review of the single source file.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "covid19"
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

def test_sklearn_calls(calls_by_top):
    assert "sklearn" in calls_by_top
    assert len(calls_by_top["sklearn"]) >= 30

def test_matplotlib_calls(calls_by_top):
    assert "matplotlib" in calls_by_top

def test_numpy_calls(calls_by_top):
    assert "numpy" in calls_by_top

def test_pandas_calls(calls_by_top):
    assert "pandas" in calls_by_top


# ── Stdlib modules (need import → correctly third-party) ──────────────

def test_datetime_is_third_party(calls_by_top):
    """datetime needs import, so it is correctly a third-party top_library."""
    assert "datetime" in calls_by_top

# ── Known issues ───────────────────────────────────────────────────────

def test_local_vars_not_top(calls_by_top):
    assert "forecast_dates" not in calls_by_top
