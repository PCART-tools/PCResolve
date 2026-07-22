## @package tests.test_regression_imported_python_result_ownership
#  Regression tests for import-backed call ownership and Python result objects.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pcresolve.cross_file import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "imported_python_result_ownership")
FUNCTION_LOCAL_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "function_local_result_ownership")


def _call(result, expression):
    matches = [
        call for call in result.all_api_calls
        if call.expression == expression
    ]
    assert len(matches) == 1
    return matches[0]


def _analyze():
    return analyze_project(FIXTURE, scope_model="v2")


def test_imported_callable_keeps_its_library_owner():
    result = _analyze()

    assert _call(result, "json.dumps({'key': 'value'})").top_library == "json"
    assert _call(result, "re.sub('x', '', json_text)").top_library == "re"
    assert _call(result, "pattern.sub('', json_text)").top_library == "re"


def test_json_dumps_result_is_python_owned():
    result = _analyze()

    assert _call(result, "json_text.encode()").top_library == "python"


def test_json_load_results_are_python_owned():
    result = _analyze()

    loads_call = _call(result, "json.loads('[{\"key\": \"value\"}]')")
    assert loads_call.top_library == "json"
    append_call = _call(
        result, "json_value.append({'other': 'value'})")
    assert append_call.top_library == "python"
    assert _call(result, "json_item.get('key')").top_library == "python"
    assert _call(result, "loaded_value.get('key')").top_library == "python"


def test_same_library_result_chain_keeps_matplotlib_owner():
    result = _analyze()

    assert _call(result, "plt.figure()").top_library == "matplotlib"
    assert _call(result, "figure.add_subplot(111)").top_library == "matplotlib"
    assert _call(result, "axes.plot([1, 2])").top_library == "matplotlib"


def test_tuple_result_owner_is_distinct_from_unpacked_items():
    result = _analyze()

    assert _call(result, "plt.subplots().count(None)").top_library == "python"
    assert _call(result, "svd_result.count(None)").top_library == "python"
    assert _call(
        result, "left_singular.dot(right_singular)").top_library == "numpy"


def test_local_tuple_return_does_not_claim_python_item_owner():
    result = _analyze()

    call = _call(result, "left_frame.head()")
    assert call.top_library != "python"


def test_receiver_preserving_ufunc_requires_receiver_evidence():
    result = _analyze()

    unresolved = _call(result, "np.log(value).diff()")
    assert unresolved.top_library == "unknown"
    known = _call(result, "np.log(known_series).diff()")
    assert known.top_library == "pandas"
    reduced = _call(result, "np.exp(-np.sum(known_array)).sum()")
    assert reduced.top_library == "numpy"
    arithmetic = _call(
        result, "np.exp(-(known_array * known_array)).sum()")
    assert arithmetic.top_library == "numpy"


def test_function_local_import_result_keeps_explicit_owner():
    result = _analyze()

    call = _call(result, "local_axes.scatter([1], [2])")
    assert call.top_library == "matplotlib"


def test_nested_result_owner_survives_cross_file_resolution():
    result = analyze_project(FUNCTION_LOCAL_FIXTURE, scope_model="v2")

    call = _call(result, "local_only_axes.scatter([1], [2])")
    assert call.top_library == "matplotlib"


def test_re_sub_results_are_python_owned():
    result = _analyze()

    assert _call(result, "clean_text.replace('a', 'b')").top_library == "python"
    assert _call(result, "pattern_text.strip()").top_library == "python"


def test_re_match_group_result_is_python_owned():
    result = _analyze()

    assert _call(result, "match.group(1)").top_library == "re"
    assert _call(result, "group_text.strip()").top_library == "python"


def test_false_sentinel_does_not_replace_imported_return_owner():
    result = _analyze()

    assert _call(result, "conditional_match.end()").top_library == "re"
    assert _call(result, "conditional_match.group(0)").top_library == "re"
    assert _call(result, "conditional_group.strip()").top_library == "python"


def test_chained_re_sub_result_is_python_owned():
    result = _analyze()

    call = _call(result, "re.sub('y', '', json_text).upper()")
    assert call.top_library == "python"


def test_import_alias_results_are_python_owned():
    result = _analyze()

    assert _call(result, "alias_text.strip()").top_library == "python"
    assert _call(result, "imported_text.encode()").top_library == "python"


def test_local_methods_with_same_names_remain_local():
    result = _analyze()

    assert _call(result, "local_dump.encode()").top_library == "local"
    assert _call(result, "local_sub.strip()").top_library == "local"


def test_shadowed_import_name_does_not_use_module_result_contract():
    result = _analyze()

    call = _call(result, "shadowed_text.encode()")
    assert call.top_library != "python"


def test_local_function_container_result_is_python_owned():
    result = _analyze()

    assert _call(result, "mapping.get('key')").top_library == "python"


def test_chained_local_function_container_results_are_python_owned():
    result = _analyze()

    setdefault = _call(
        result, "make_mapping().setdefault('key', 'value')")
    append = _call(result, "make_list().append('value')")
    assert setdefault.top_library == "python"
    assert append.top_library == "python"


def test_mixed_local_function_returns_do_not_overclaim_python():
    result = _analyze()

    call = _call(result, "mixed_result.get('key')")
    assert call.top_library == "unknown"


def test_builtin_base_methods_are_python_owned():
    result = _analyze()

    assert _call(result, "python_list.append('value')").top_library == "python"
    assert _call(result, "indirect_list.extend(['value'])").top_library == "python"


def test_local_override_of_builtin_base_method_remains_local():
    result = _analyze()

    call = _call(result, "override_list.append('value')")
    assert call.top_library == "local"
