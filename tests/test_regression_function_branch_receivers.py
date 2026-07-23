## @package tests.test_regression_function_branch_receivers
#  Regression tests for branch-dependent receiver ownership in functions.

import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "function_branch_receivers")


def _close_calls():
    result = analyze_project(FIXTURE, scope_model="v2")
    return [
        call for call in result.all_api_calls
        if call.expression == "stream.close()"
    ]


def test_two_imported_branch_receivers_remain_unknown():
    calls = _close_calls()
    call = next(call for call in calls if call.lineno == 20)
    assert call.top_library == "unknown"


def test_local_and_imported_branch_receivers_remain_unknown():
    calls = _close_calls()
    call = next(call for call in calls if call.lineno == 28)
    assert call.top_library == "unknown"


def test_same_category_function_branches_converge():
    result = analyze_project(FIXTURE, scope_model="v2")
    calls = {call.expression: call for call in result.all_api_calls}

    assert calls["values.append(1)"].top_library == "python"
    assert calls["reader.close()"].top_library == "local"
