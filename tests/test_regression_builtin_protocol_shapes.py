## @package tests.test_regression_builtin_protocol_shapes
#  Regression coverage for evidence-backed Python protocol shapes.

import os

import pytest

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "builtin_protocol_shapes")


@pytest.fixture(scope="module")
def calls():
    return analyze_project(FIXTURE).all_api_calls


def _call(calls, expression):
    matches = [call for call in calls if call.expression == expression]
    assert len(matches) == 1, (expression, [
        call.expression for call in calls
    ])
    return matches[0]


@pytest.mark.parametrize("expression", [
    "text.strip()",
    "trimmed.replace('alpha', 'gamma')",
    "replaced.split(',')",
    "first.upper()",
    "text.expandtabs()",
    "part.rstrip()",
    "values.append(1)",
    "values.__len__()",
    "values.__iter__()",
    "text.startswith('r')",
    "annotated.endswith('x')",
    "formatted.encode('utf-8')",
])
def test_known_builtin_protocol_shapes_are_python(calls, expression):
    assert _call(calls, expression).top_library == "python"


def test_unresolved_parameter_does_not_guess_string(calls):
    assert _call(calls, "value.strip()").top_library == "unknown"


def test_isinstance_guard_narrows_builtin_receiver_shape(calls):
    assert _call(
        calls, "value.encode('utf-8')"
    ).top_library == "python"


def test_local_function_python_shape_flows_to_result_receiver(calls):
    assert _call(calls, "local_string_factory()").top_library == "local"
    assert _call(
        calls, "factory_value.replace('a', 'b')"
    ).top_library == "python"


def test_mixed_python_and_local_returns_remain_unknown(calls):
    assert _call(
        calls, "mixed_value.replace('a', 'b')"
    ).top_library == "unknown"


def test_local_same_named_method_remains_local(calls):
    assert _call(
        calls, "value.replace('a', 'b')"
    ).top_library == "local"


def test_overloaded_mod_result_does_not_gain_string_shape(calls):
    assert _call(
        calls, "formatted.replace('a', 'b')"
    ).top_library == "local"


def test_verified_imported_method_result_preserves_python_shape(calls):
    assert _call(calls, "match.group(0)").top_library == "re"
    assert _call(calls, "group.strip()").top_library == "python"


def test_local_same_named_method_result_does_not_gain_python_shape(calls):
    assert _call(
        calls, "group.replace('a', 'b')"
    ).top_library == "local"
