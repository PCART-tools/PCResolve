## @package tests.test_deep_graph_kernels
#  Test pcresolve against the Deep-Graph-Kernels project oracle.
#
#  Deep-Graph-Kernels is a Kronecker graph generation script (1 file).
#  It uses: numpy, scipy, networkx, apgl.
#
#  Oracle built by code review of the single source file.

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tested_projects", "Deep-Graph-Kernels"
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

def test_scipy_calls(calls_by_top):
    assert "scipy" in calls_by_top

def test_apgl_calls(calls_by_top):
    assert "apgl" in calls_by_top

def test_networkx_calls(calls_by_top):
    assert "networkx" in calls_by_top


# ── Known issues ───────────────────────────────────────────────────────

@pytest.mark.xfail(reason="KNOWN: Parameter (apgl class, import not visible) leaks (2 calls)")
def test_parameter_is_apgl(calls_by_top):
    assert "Parameter" not in calls_by_top
