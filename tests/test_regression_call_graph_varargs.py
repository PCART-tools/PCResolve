import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "call_graph_varargs")


def _reshape_calls():
    return [
        call for call in analyze_project(FIXTURE).all_api_calls
        if call.expression == "value.reshape(1, -1)"
    ]


def test_star_args_forwarding_preserves_receiver_owner():
    calls = _reshape_calls()
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_star_kwargs_forwarding_preserves_receiver_owner():
    calls = _reshape_calls()
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"
