## @package tests.test_regression_loop_carried_python_shape
#  Regression coverage for bounded loop-carried Python value shapes.

import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "loop_carried_python_shape"
)


def _calls():
    result = analyze_project(FIXTURE)
    return {
        (call.lineno, call.expression): call
        for call in result.all_api_calls
    }


def test_loop_carried_builtin_shape_reaches_next_iteration():
    calls = _calls()
    assert calls[(10, "carried.add(value)")].top_library == "python"


def test_preheader_binding_blocks_conflicting_loop_shape():
    calls = _calls()
    assert calls[(21, "carried.add(value)")].top_library != "python"


def test_while_loop_carries_builtin_shape_to_next_iteration():
    calls = _calls()
    assert calls[(32, "carried.append(values[index])")].top_library == "python"


def test_async_for_carries_builtin_shape_to_next_iteration():
    calls = _calls()
    assert calls[(42, "carried.add(value)")].top_library == "python"


def test_tuple_rebinding_blocks_loop_shape_promotion():
    calls = _calls()
    assert calls[(51, "carried.add(value)")].top_library != "python"


def test_definition_rebinding_blocks_loop_shape_promotion():
    calls = _calls()
    assert calls[(62, "carried.add(value)")].top_library != "python"
