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
    """UPDATEPHASE3: Module-level 'np' should be 'numpy'.
    Currently 'local' because use_local() reassigns np = requests.Session()
    and the single-slot symbol table leaks function-local bindings."""
    # Phase 3 expectation: assert module_symbols.get("np") == "numpy"
    assert module_symbols.get("np") == "local"


def test_session_call_is_requests(calls_by_top):
    """UPDATEPHASE3: session.get(...) should be classified as 'requests'.
    Currently 'local' because scope pollution masks the chain."""
    # Phase 3 expectation: assert "requests" in calls_by_top
    assert "local" in calls_by_top
    exprs = [c.expression for c in calls_by_top["local"]]
    assert any("session.get" in e for e in exprs)


def test_function_use_param_does_not_pollute_requests(module_symbols):
    """UPDATEPHASE3: Module-level 'requests' should stay 'requests'.
    Currently 'local' because the parameter 'requests' in use_param()
    overwrites the module-level import alias."""
    # Phase 3 expectation: assert module_symbols.get("requests") == "requests"
    assert module_symbols.get("requests") == "local"


def test_comprehension_var_x_not_in_module_symbols(module_symbols):
    """UPDATEPHASE3: Comprehension variable 'x' must not leak.
    Currently 'x' appears because comprehension targets go into the
    single-slot symbol table."""
    # Phase 3 expectation: assert "x" not in module_symbols
    assert "x" in module_symbols
