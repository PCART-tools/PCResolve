## @package tests.test_regression_callsite_chains
#  Regression tests: same-named local vars in different functions
#  must eventually have distinct call-site chains (phase 4).
#  For now, locks current behaviour.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "regression_callsite_chains")


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


def test_single_file_analyzed(result):
    assert len(result.files) == 1


def test_both_functions_calls_exist(result):
    """Both first() and second() contain call expressions."""
    exprs = {c.expression for c in result.all_api_calls}
    assert any("get" in e for e in exprs)
    assert any("reshape" in e for e in exprs)


def test_requests_and_numpy_calls_classified(result):
    """Verify that both requests and numpy calls are detected."""
    tops = {c.top_library for c in result.all_api_calls}
    assert "requests" in tops
    assert "numpy" in tops
