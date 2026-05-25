## @package tests.test_regression_branch_imports
#  Regression tests: branch imports lock current behaviour.
#  Expected to evolve in phase 5 with SourceSet alternatives.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "regression_branch_imports")


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


def test_single_file_analyzed(result):
    assert len(result.files) == 1


def test_lib_array_call_is_pandas(result):
    """UPDATEPHASE5: lib.array([1]) currently resolves to pandas because
    the else branch is visited last and overwrites the if-branch import.
    After phase 5 (multi-value binding) this should become alternatives:
    [numpy, pandas]."""
    # Phase 5 expectation: assert tops == {"numpy", "pandas"}
    lib_calls = [c for c in result.all_api_calls if "lib" in c.expression]
    assert len(lib_calls) == 1
    assert lib_calls[0].top_library == "pandas"
