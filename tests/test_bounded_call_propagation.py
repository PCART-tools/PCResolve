## @package tests.test_bounded_call_propagation
#  Regression tests for bounded context-sensitive project call propagation.

import os

from pcresolve import analyze_project


_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "bounded_call_propagation")


def _calls():
    return analyze_project(_FIXTURE).all_api_calls


def _call(expression):
    matches = [call for call in _calls() if call.expression == expression]
    assert len(matches) == 1, (expression, matches)
    return matches[0]


def _call_at(expression, file_name, lineno):
    matches = [
        call for call in _calls()
        if call.expression == expression
        and call.file_path.endswith(file_name)
        and call.lineno == lineno
    ]
    assert len(matches) == 1, (expression, file_name, lineno, matches)
    return matches[0]


def test_cross_file_return_parameter_is_callsite_sensitive():
    assert _call("frame_result.head()").top_library == "pandas"
    assert _call("array_result.reshape(1, -1)").top_library == "numpy"


def test_reassigned_result_name_keeps_each_callsite_context():
    assert _call("reused_result.reshape(1, -1)").top_library == "numpy"
    assert _call("reused_result.head()").top_library == "pandas"


def test_nested_local_return_substitutes_original_argument():
    assert _call("relay_result.reshape(1, -1)").top_library == "numpy"


def test_cross_file_parameter_receiver_uses_unique_call_edge():
    call = _call_at("value.reshape(1, -1)", "provider.py", 10)
    assert call.top_library == "numpy"


def test_conflicting_parameter_receiver_remains_unknown():
    assert _call("value.mean()").top_library == "unknown"


def test_uncalled_parameter_receiver_remains_unknown():
    call = _call_at("value.reshape(1, -1)", "provider.py", 18)
    assert call.top_library == "unknown"


def test_constructor_parameter_flows_through_self_attribute_return():
    assert _call("held.head()").top_library == "pandas"


def test_recursive_return_propagation_terminates_conservatively():
    assert _call("recursive_result.reshape(1, -1)").top_library in (
        "numpy", "unknown")
