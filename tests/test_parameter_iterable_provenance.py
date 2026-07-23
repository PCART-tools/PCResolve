import os

from pcresolve.cross_file import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__),
    "fixtures",
    "parameter_iterable_provenance",
)


def _calls(result, function_name):
    return [
        call for call in result.all_api_calls
        if call.func_name == function_name
    ]


def test_parameter_iterable_preserves_concrete_python_element_shape():
    result = analyze_project(FIXTURE, scope_model="v2")
    calls = _calls(result, "item.strip")
    assert len(calls) == 4
    by_line = {call.lineno: call for call in calls}
    assert by_line[3].top_library == "python"
    assert by_line[12].top_library == "python"
    assert by_line[25].top_library == "unknown"
    assert by_line[32].top_library == "unknown"


def test_unresolved_parameter_iterable_does_not_become_local():
    result = analyze_project(FIXTURE, scope_model="v2")
    calls = _calls(result, "item.strip")
    assert calls[2].top_library == "unknown"


def test_unresolved_iterator_element_does_not_become_local():
    result = analyze_project(FIXTURE, scope_model="v2")
    calls = _calls(result, "item.strip")
    assert calls[3].top_library == "unknown"
