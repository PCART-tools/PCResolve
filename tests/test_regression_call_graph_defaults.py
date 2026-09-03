import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "call_graph_defaults")


def _calls(expression):
    return [
        call for call in analyze_project(FIXTURE).all_api_calls
        if call.expression == expression
    ]


def test_default_positional_argument_preserves_numpy_owner():
    calls = _calls("value.reshape(1, -1)")
    assert len(calls) == 2
    assert all(call.top_library == "numpy" for call in calls)


def test_default_list_argument_preserves_python_owner():
    calls = _calls("value.append(1)")
    assert len(calls) == 1
    assert calls[0].top_library == "python"
