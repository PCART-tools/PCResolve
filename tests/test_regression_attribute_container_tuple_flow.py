## @package tests.test_regression_attribute_container_tuple_flow
#  Regression coverage for tuple items stored in attribute-backed lists.

import os

import pytest

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "attribute_container_tuple_flow")


@pytest.fixture(scope="module")
def calls():
    return analyze_project(FIXTURE).all_api_calls


def _calls(calls, expression):
    return [call for call in calls if call.expression == expression]


def test_attribute_container_tuple_fields_survive_iteration(calls):
    left_calls = _calls(calls, "left.finditer(text)")
    right_calls = _calls(calls, "right.finditer(text)")

    assert len(left_calls) == 3
    assert len(right_calls) == 3
    assert left_calls[0].top_library == "re"
    assert right_calls[0].top_library == "re"
    assert _calls(calls, "match.start()")[0].top_library == "re"
    assert _calls(calls, "match.end()")[0].top_library == "re"


def test_conflicting_attribute_container_items_stay_unresolved(calls):
    left_calls = _calls(calls, "left.finditer(text)")
    right_calls = _calls(calls, "right.finditer(text)")

    assert left_calls[1].top_library != "re"
    assert right_calls[1].top_library != "re"


def test_rebound_attribute_container_drops_stale_item_sources(calls):
    left_calls = _calls(calls, "left.finditer(text)")
    right_calls = _calls(calls, "right.finditer(text)")

    assert left_calls[2].top_library != "re"
    assert right_calls[2].top_library != "re"
