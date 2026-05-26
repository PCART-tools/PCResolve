## @package tests.test_regression_multiple_returns
#  Regression tests: multiple return paths lock current behaviour.
#  After phase 5, make() return source should be SourceSet([requests, numpy]).

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "regression_multiple_returns")


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


def test_single_file_analyzed(result):
    assert len(result.files) == 1


def test_value_get_call_exists(result):
    """value.get(...) call should exist in the output."""
    exprs = [c.expression for c in result.all_api_calls]
    assert any("get" in e for e in exprs)


def test_make_return_call_classified(result):
    """make(True) itself is a local function call."""
    local_calls = [c for c in result.all_api_calls if c.top_library == "local"]
    assert len(local_calls) >= 1
    exprs = [c.expression for c in local_calls]
    assert any("make" in e for e in exprs)


def test_value_get_has_multi_source(result):
    """UPDATEPHASE5: value.get(...) traces to either requests or numpy
    depending on which return source is resolved first. The chain is now
    SourceSet([requests.Session, np.array]), with the first match winning.
    Full alternatives support needs classification engine (Phase 8A)."""
    value_calls = [c for c in result.all_api_calls if "get" in c.expression]
    assert len(value_calls) == 1
    assert value_calls[0].top_library in ("requests", "numpy")
