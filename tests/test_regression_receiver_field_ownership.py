## @package tests.test_regression_receiver_field_ownership
#  Regression tests for explicit import-backed receiver fields.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "receiver_field_ownership")


def _call(result, expression):
    matches = [call for call in result.all_api_calls
               if call.expression == expression]
    assert len(matches) == 1, expression
    return matches[0]


def test_direct_import_result_bound_to_instance_field_keeps_owner():
    result = analyze_project(FIXTURE)
    call = _call(result, "self.values.reshape(1)")
    assert call.top_library == "numpy"


def test_subscripted_instance_field_keeps_owner():
    result = analyze_project(FIXTURE)
    calls = [call for call in result.all_api_calls
             if call.expression == "self.values[0].reshape(1)"]
    assert calls
    assert all(call.top_library == "numpy" for call in calls)


def test_chained_subscripted_instance_field_keeps_owner():
    result = analyze_project(FIXTURE)
    expression = "self.values[0].reshape(1).dot(self.values[0])"
    calls = [call for call in result.all_api_calls
             if call.expression == expression]
    assert calls
    assert all(call.top_library == "numpy" for call in calls)


def test_deep_chained_subscripted_instance_field_keeps_owner():
    result = analyze_project(FIXTURE)
    call = _call(
        result,
        "self.values[0].reshape(1).dot(self.values[0]).dot(self.values[0])")
    assert call.top_library == "numpy"


def test_variable_receiver_result_is_not_producer_library():
    result = analyze_project(FIXTURE)
    call = _call(result, "self.results.append(2)")
    assert call.top_library != "multiprocessing"


def test_direct_import_object_field_keeps_module_owner():
    result = analyze_project(FIXTURE)
    call = _call(result, "self.pool.close()")
    assert call.top_library == "multiprocessing"
