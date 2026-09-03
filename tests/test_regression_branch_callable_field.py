## @package tests.test_regression_branch_callable_field

import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "branch_callable_field")


def _call(expression):
    result = analyze_project(FIXTURE)
    calls = [
        call for call in result.all_api_calls
        if call.expression == expression
    ]
    assert len(calls) == 1
    return calls[0]


def test_branch_callable_results_converge_on_one_owner():
    call = _call("result.reshape(1, -1)")
    assert call.top_library == "numpy"


def test_branch_callable_result_conflict_stays_unknown():
    call = _call("result.copy()")
    assert call.top_library == "unknown"


def test_branch_callable_missing_return_stays_unknown():
    call = _call("result.reshape(-1)")
    assert call.top_library == "unknown"
