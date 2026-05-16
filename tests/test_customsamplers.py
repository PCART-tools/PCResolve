## @package tests.test_customsamplers
#  Test pcresolve against the CustomSamplers project oracle.
#
#  CustomSamplers is a simple matplotlib/numpy plot script (1 file).
#  It uses: numpy, matplotlib.
#
#  Oracle built by code review of the single source file.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "CustomSamplers"
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

def test_numpy_calls(calls_by_top):
    assert "numpy" in calls_by_top

def test_matplotlib_calls(calls_by_top):
    assert "matplotlib" in calls_by_top
    assert len(calls_by_top["matplotlib"]) == 7

def test_all_calls_correct(calls_by_top):
    """All 8 calls are correctly classified — no local/python needed here."""
    total = sum(len(v) for v in calls_by_top.values())
    assert total == 8
    assert set(calls_by_top.keys()) == {"numpy", "matplotlib"}
