## @package tests.test_regression_local_container_item_fields
#  Regression tests for local container element field shape propagation.

import os

from pcresolve import analyze_project


_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "local_container_item_fields")


def _call(expression):
    calls = [
        call for call in analyze_project(_FIXTURE).all_api_calls
        if call.expression == expression
    ]
    assert len(calls) == 1, (expression, calls)
    return calls[0]


def test_dict_field_appended_through_local_list_is_python():
    call = _call("segment['tokens'].append(value)")
    assert call.top_library == "python"


def test_local_methods_remain_local():
    assert _call("buffer.add_segment()").top_library == "local"
    assert _call("buffer.append_token('word')").top_library == "local"


def test_mixed_local_container_elements_do_not_infer_python_shape():
    assert _call("entry['tokens'].append(value)").top_library != "python"


def test_local_list_append_preserves_element_fields():
    assert _call("local_entry['tokens'].append(value)").top_library == "python"
