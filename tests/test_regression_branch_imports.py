## @package tests.test_regression_branch_imports
#  Regression tests: branch imports with multi-value SourceSet after phase 5.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pcresolve import analyze_project
from pcresolve.sources import SourceSet

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "regression_branch_imports")


@pytest.fixture(scope="module")
def result_v1():
    return analyze_project(FIXTURE, scope_model="v1")


@pytest.fixture(scope="module")
def result_v2():
    return analyze_project(FIXTURE, scope_model="v2")


def test_single_file_analyzed_v1(result_v1):
    assert len(result_v1.files) == 1


def test_single_file_analyzed_v2(result_v2):
    assert len(result_v2.files) == 1


def test_lib_array_call_is_pandas_v1(result_v1):
    """v1: last branch wins, so lib -> pandas."""
    lib_calls = [c for c in result_v1.all_api_calls if "lib" in c.expression]
    assert len(lib_calls) == 1
    assert lib_calls[0].top_library == "pandas"


def test_lib_array_call_has_alternatives_v2(result_v2):
    """v2: branch merging produces SourceSet, top should be numpy or pandas."""
    lib_calls = [c for c in result_v2.all_api_calls if "lib" in c.expression]
    assert len(lib_calls) == 1
    assert lib_calls[0].top_library in ("numpy", "pandas")
    assert "SourceSet(" not in str(lib_calls[0].top_library)


def test_branch_imports_no_sourceset_leak(result_v2):
    """No SourceSet repr in library_usage keys or top_library."""
    for call in result_v2.all_api_calls:
        assert "SourceSet(" not in str(call.top_library)
    for lib in result_v2.library_usage:
        assert "SourceSet(" not in str(lib)
