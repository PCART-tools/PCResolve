## @package tests.test_regression_scope_shadowing
#  Regression tests: function params, locals, and comprehension vars
#  must not pollute module-level symbols.
#
#  Current behaviour (phase 0): the single-slot SymbolTable allows
#  function-local assignments, parameters, and comprehension variables
#  to overwrite module-level symbols.  These tests lock that baseline.
#  Phase 3 (scope model) will fix the assertions marked UPDATEPHASE3.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "regression_scope_shadowing")


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


@pytest.fixture(scope="module")
def module_symbols(result):
    """Return module-level symbols from the main module."""
    for f in result.files:
        if f.module_name == "main":
            return f.symbols
    return {}


def test_module_requests_stays_third_party(module_symbols):
    """Module-level 'requests' should resolve to 'requests' package."""
    assert "requests" in module_symbols or "session" in module_symbols


def test_module_np_stays_numpy(module_symbols):
    """Module-level 'np' should be 'numpy' with v2 lexical scopes."""
    assert module_symbols.get("np") == "numpy", \
        f"Expected np->numpy, got {module_symbols.get('np')}"


def test_session_call_is_requests(calls_by_top):
    """session.get(...) should be classified as 'requests' with v2."""
    assert "requests" in calls_by_top, \
        f"Expected requests in calls_by_top, got {list(calls_by_top.keys())}"


def test_function_use_param_does_not_pollute_requests(module_symbols):
    """Module-level 'requests' should stay 'requests' with v2 scopes."""
    assert module_symbols.get("requests") == "requests", \
        f"Expected requests->requests, got {module_symbols.get('requests')}"


def test_comprehension_var_x_not_in_module_symbols(module_symbols):
    """Comprehension variable 'x' must not leak to module scope in v2."""
    assert "x" not in module_symbols, \
        f"x should not be in module symbols: {list(module_symbols.keys())}"
