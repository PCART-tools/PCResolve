## @package tests.test_regression_callback_map_result_field
#  Regression coverage for bounded callback-result container fields.

import os

import pytest

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "callback_map_result_field")


@pytest.fixture(scope="module")
def calls():
    return analyze_project(FIXTURE).all_api_calls


def _calls(calls, expression):
    return [call for call in calls if call.expression == expression]


def test_map_callback_return_propagates_to_instance_field_item(calls):
    matches = _calls(calls, "self.handlers[0]('{}')")
    assert len(matches) == 1
    assert matches[0].top_library == "json"


def test_mixed_callback_returns_remain_unknown(calls):
    matches = _calls(calls, "self.mixed[0]('{}')")
    assert len(matches) == 1
    assert matches[0].top_library == "unknown"


def test_field_rebind_stops_map_result_propagation(calls):
    matches = _calls(calls, "self.handlers[0]('value')")
    assert len(matches) == 1
    assert matches[0].top_library == "local"
