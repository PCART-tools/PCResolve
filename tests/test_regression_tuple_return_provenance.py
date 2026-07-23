import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "tuple_return_provenance")
MIXED_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "heterogeneous_tuple_return")


def test_tuple_return_items_preserve_cross_file_owner():
    result = analyze_project(FIXTURE)
    calls = [
        call
        for call in result.all_api_calls
        if call.expression in ("left.reshape(1, -1)",
                               "right.reshape(1, -1)")
    ]
    assert len(calls) == 2
    assert all(call.top_library == "numpy" for call in calls)


def test_heterogeneous_tuple_items_do_not_share_one_owner():
    result = analyze_project(MIXED_FIXTURE)
    calls = {
        call.expression: call
        for call in result.all_api_calls
        if call.expression in ("left.reshape(1, -1)", "right.upper()")
    }
    assert calls["left.reshape(1, -1)"].top_library == "numpy"
    assert calls["right.upper()"].top_library == "python"


def test_heterogeneous_tuple_items_keep_position_when_forwarded():
    result = analyze_project(MIXED_FIXTURE)
    calls = {
        call.expression: call
        for call in result.all_api_calls
        if call.expression in (
            "left_value.reshape(1, -1)", "right_value.upper()")
    }
    assert calls["left_value.reshape(1, -1)"].top_library == "numpy"
    assert calls["right_value.upper()"].top_library == "python"


def test_tuple_positions_survive_same_name_rebinding():
    result = analyze_project(MIXED_FIXTURE)
    calls = {
        call.expression: call
        for call in result.all_api_calls
        if call.expression in (
            "left_value.reshape(2, -1)", "right_value.lower()")
    }
    assert calls["left_value.reshape(2, -1)"].top_library == "numpy"
    assert calls["right_value.lower()"].top_library == "python"


def test_tuple_item_owner_survives_following_method_assignment():
    result = analyze_project(FIXTURE)
    calls = [
        call for call in result.all_api_calls
        if call.expression in (
            "left.reshape(1, -1)", "left_view.reshape(2, 1)")
    ]
    assert len(calls) == 2
    assert all(call.top_library == "numpy" for call in calls)
