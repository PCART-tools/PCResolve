## @package tests.test_parameter_subscript_receiver
#  Regression tests for parameter-backed subscript receivers.

import os

from pcresolve import analyze_project


_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "parameter_subscript_receiver")


def test_subscripted_parameter_preserves_unique_receiver_owner():
    calls = analyze_project(_FIXTURE).all_api_calls
    matches = [
        call for call in calls
        if call.expression == "values[0].reshape(1, -1)"
    ]
    assert len(matches) == 1
    assert matches[0].top_library == "numpy"


def test_uncalled_subscripted_parameter_remains_unknown():
    calls = analyze_project(_FIXTURE).all_api_calls
    matches = [
        call for call in calls
        if call.expression == "values[0].reshape(2, -1)"
    ]
    assert len(matches) == 1
    assert matches[0].top_library == "unknown"


def test_forwarded_subscripted_parameter_preserves_receiver_owner():
    calls = analyze_project(_FIXTURE).all_api_calls
    matches = [
        call for call in calls
        if call.expression == "values[0].reshape(3, -1)"
    ]
    assert len(matches) == 1
    assert matches[0].top_library == "numpy"


def test_dynamic_subscripted_parameter_preserves_receiver_owner():
    calls = analyze_project(_FIXTURE).all_api_calls
    matches = [
        call for call in calls
        if call.expression == "values[key].reshape(4, -1)"
    ]
    assert len(matches) == 1
    assert matches[0].top_library == "numpy"


def test_nested_parameter_subscript_preserves_receiver_owner():
    calls = analyze_project(_FIXTURE).all_api_calls
    matches = [
        call for call in calls
        if call.expression == "value.mean()"
    ]
    assert len(matches) == 1
    assert matches[0].top_library == "numpy"
