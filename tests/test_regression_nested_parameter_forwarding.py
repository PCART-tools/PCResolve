import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "nested_parameter_forwarding")


def test_nested_local_parameter_forwarding_preserves_numpy_owner():
    calls = analyze_project(FIXTURE).all_api_calls
    matches = [
        call for call in calls
        if call.expression == "value.reshape(1, -1)"
    ]

    assert len(matches) == 1
    assert matches[0].top_library == "numpy"


def test_nested_forwarding_has_no_uncovered_call_site():
    calls = analyze_project(FIXTURE).all_api_calls

    assert any(call.expression == "reshape_twice(array_value)"
               for call in calls)
    assert any(call.expression == "reshape_once(value)"
               for call in calls)
