## @package tests.test_regression_call_graph_callback_map
#  Regression coverage for bounded local callback parameter propagation.

import os

import pytest

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "call_graph_callback_map")


@pytest.fixture(scope="module")
def calls():
    return analyze_project(FIXTURE).all_api_calls


def _call(calls, expression):
    matches = [call for call in calls if call.expression == expression]
    assert len(matches) == 1, (expression, [
        call.expression for call in calls
    ])
    return matches[0]


def test_pool_map_propagates_tuple_field_python_shape(calls):
    assert _call(calls, "name.strip()").top_library == "python"
    assert _call(calls, "count.bit_length()").top_library == "python"


def test_unrelated_map_without_local_callback_stays_conservative(calls):
    assert _call(calls, "pool.map(handle, items)").top_library == (
        "multiprocessing")


def test_conflicting_tuple_append_does_not_propagate_stale_shape(calls):
    call = _call(calls, "value.strip()")
    assert call.top_library != "python"
