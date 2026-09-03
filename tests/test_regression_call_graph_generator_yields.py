import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "call_graph_generator_yields")


def _calls(expression):
    return [
        call for call in analyze_project(FIXTURE).all_api_calls
        if call.expression == expression
    ]


def test_generator_yield_preserves_numpy_element_owner():
    calls = _calls("array_value.reshape(1, -1)")
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_generator_yield_preserves_python_container_owner():
    calls = _calls("list_value.append(1)")
    assert len(calls) == 1
    assert calls[0].top_library == "python"


def test_generator_yield_stops_at_a_later_rebinding():
    calls = _calls("rebound_value.append(1)")
    assert len(calls) == 1
    assert calls[0].top_library == "python"


def test_cross_file_generator_yield_preserves_element_owner():
    cross_fixture = os.path.join(
        os.path.dirname(__file__), "fixtures",
        "call_graph_generator_yields_cross_file")
    calls = [
        call for call in analyze_project(cross_fixture).all_api_calls
        if call.expression in (
            "array_value.reshape(1, -1)",
            "list_value.append(1)",
        )
    ]
    assert {call.expression: call.top_library for call in calls} == {
        "array_value.reshape(1, -1)": "numpy",
        "list_value.append(1)": "python",
    }
