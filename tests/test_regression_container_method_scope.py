# 1.0.5: container method classification must distinguish module-level
# containers (python) from function-local containers (local).
# Regression test for hfhd container fix over-reach:
# stp.append(...) and Sigma_hat_list.append(...) should be local,
# while module-level list.append() and dict.get() should stay python.

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


def test_function_local_list_append_is_local():
    """local_list.append(1) inside helper_build_list() should be local."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "local_list.append(1)")
    assert call is not None, "local_list.append(1) not found"
    assert call.top_library == "local", \
        f"Expected local, got {call.top_library} for {call.expression}"


def test_function_local_listcomp_append_is_local():
    """local_listcomp.append(4) inside helper_build_listcomp() should be local."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "local_listcomp.append(4)")
    assert call is not None, "local_listcomp.append(4) not found"
    assert call.top_library == "local", \
        f"Expected local, got {call.top_library} for {call.expression}"
