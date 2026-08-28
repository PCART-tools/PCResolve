## @package tests.test_regression_inherited_call_result
#  Regression coverage for inherited local method return propagation.

import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "inherited_call_result"
)


def _calls():
    result = analyze_project(FIXTURE)
    return {
        call.expression: call
        for call in result.all_api_calls
    }


def test_inherited_method_result_uses_base_implementation():
    calls = _calls()
    assert calls["callback('{}')"].top_library == "json"


def test_overridden_method_result_uses_nearest_implementation():
    calls = _calls()
    assert calls["override_callback(4)"].top_library == "math"
