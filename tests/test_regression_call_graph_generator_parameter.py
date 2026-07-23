import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "call_graph_generator_parameter")
SAME_FILE = os.path.join(FIXTURE, "same_file")


def _calls(root):
    return analyze_project(root).all_api_calls


def test_generator_yield_parameter_preserves_numpy_owner():
    calls = [
        call for call in _calls(SAME_FILE)
        if call.expression == "item.reshape(1, -1)"
    ]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_generator_yield_parameter_preserves_python_owner():
    calls = [
        call for call in _calls(SAME_FILE)
        if call.expression == "item.append(1)"
    ]
    assert len(calls) == 1
    assert calls[0].top_library == "python"


def test_cross_file_generator_yield_parameter_preserves_numpy_owner():
    root = os.path.join(FIXTURE, "cross_file")
    calls = [
        call for call in _calls(root)
        if call.expression == "item.reshape(1, -1)"
    ]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"
