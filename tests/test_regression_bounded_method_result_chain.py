## @package tests.test_regression_bounded_method_result_chain

import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "bounded_method_result_chain")


def _call(expression):
    result = analyze_project(FIXTURE)
    calls = [
        call for call in result.all_api_calls
        if call.expression == expression
    ]
    assert len(calls) == 1
    return calls[0]


def test_exact_local_method_result_preserves_library_argument_owner():
    call = _call("array_value.reshape(1, -1)")
    assert call.top_library == "numpy"


def test_exact_local_method_result_preserves_python_argument_owner():
    call = _call("text_value.strip()")
    assert call.top_library == "python"


def test_conflicting_local_method_returns_remain_unknown():
    call = _call("mixed_value.copy()")
    assert call.top_library == "unknown"
