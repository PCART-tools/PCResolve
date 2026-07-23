# 1.0.5: builtin container ownership follows the receiver's concrete
# Python type in every lexical scope. Scope-aware metadata prevents a
# same-name local object in another function from inheriting that type.

from pcresolve import analyze_project
import os


FIXTURE_DIR = os.path.join(os.path.dirname(__file__),
                           "fixtures", "regression_container_method_scope")


def _find_call(calls, expression_contains):
    """Find a call whose expression contains the given substring."""
    for c in calls:
        if expression_contains in c.expression:
            return c
    return None


def test_module_level_list_append_is_python():
    """module_list.append(1) at module level should be python."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "module_list.append(1)")
    assert call is not None, "module_list.append(1) not found"
    assert call.top_library == "python", \
        f"Expected python, got {call.top_library} for {call.expression}"


def test_module_level_dict_get_is_python():
    """module_dict.get('key', 'default') at module level should be python."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "module_dict.get")
    assert call is not None, "module_dict.get(...) not found"
    assert call.top_library == "python", \
        f"Expected python, got {call.top_library} for {call.expression}"


def test_module_level_listcomp_append_is_python():
    """module_listcomp.append(4) at module level should be python."""
    result = analyze_project(FIXTURE_DIR)
    # module_listcomp.append(4) in main()
    call = _find_call(result.all_api_calls, "module_listcomp.append(4)")
    assert call is not None, "module_listcomp.append(4) not found"
    assert call.top_library == "python", \
        f"Expected python, got {call.top_library} for {call.expression}"


def test_function_local_list_append_is_python():
    """A function-local list still exposes Python's list.append."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "local_list.append(1)")
    assert call is not None, "local_list.append(1) not found"
    assert call.top_library == "python", \
        f"Expected python, got {call.top_library} for {call.expression}"


def test_function_local_listcomp_append_is_python():
    """A function-local list comprehension produces a Python list."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "local_listcomp.append(4)")
    assert call is not None, "local_listcomp.append(4) not found"
    assert call.top_library == "python", \
        f"Expected python, got {call.top_library} for {call.expression}"


def test_class_attribute_dict_values_is_python():
    """A classmethod can use the concrete class attribute container."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "cls.LOOKUP.values()")
    assert call is not None, "cls.LOOKUP.values() not found"
    assert call.top_library == "python", \
        f"Expected python, got {call.top_library} for {call.expression}"


def test_staticmethod_parameter_does_not_inherit_class_attribute_kind():
    """An ordinary staticmethod parameter is not the enclosing class."""
    result = analyze_project(FIXTURE_DIR)
    calls = [
        call for call in result.all_api_calls
        if call.expression == "cls.LOOKUP.values()"
    ]
    assert len(calls) == 2
    assert any(call.top_library == "python" for call in calls)
    assert any(call.top_library != "python" for call in calls)


def test_uniform_dynamic_dict_items_are_python():
    """Uniform direct writes establish the selected value's container kind."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "buckets['first'].append(1)")
    assert call is not None, "buckets['first'].append(1) not found"
    assert call.top_library == "python", \
        f"Expected python, got {call.top_library} for {call.expression}"


def test_conflicting_dynamic_dict_items_do_not_guess_python():
    """Different item shapes invalidate receiver-kind propagation."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "buckets[key].append(1)")
    assert call is not None, "buckets[key].append(1) not found"
    assert call.top_library != "python", \
        f"Conflicting item kinds should not produce python: {call.expression}"


def test_rebound_dict_has_fresh_item_shape():
    """A new container binding does not inherit an earlier conflict."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "buckets['second'].append(1)")
    assert call is not None, "buckets['second'].append(1) not found"
    assert call.top_library == "python", \
        f"Expected python, got {call.top_library} for {call.expression}"
