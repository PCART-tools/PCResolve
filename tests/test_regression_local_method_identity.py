"""P0: Local method call identity protection.

Methods explicitly defined in project-local classes must be
classified as local regardless of what library APIs the method body
calls internally.
"""

from pcresolve import analyze_project
import os


FIXTURE_DIR = os.path.join(os.path.dirname(__file__),
                           "fixtures", "local_method_identity")


def _find_call(calls, expression_contains):
    for c in calls:
        if expression_contains in c.expression:
            return c
    return None


def test_module_instance_local_method_is_local():
    """client.do_load(...) where client=Client() → local."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "client.do_load(")
    assert call is not None, "client.do_load(...) not found"
    assert call.top_library == "local", (
        "client.do_load() should be local, got %s" % call.top_library)


def test_library_backend_method_stays_library():
    """client.backend.loads(...) where backend=json → json."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "client.backend.loads(")
    assert call is not None, "client.backend.loads(...) not found"
    assert call.top_library == "json", (
        "client.backend.loads() should be json, got %s" % call.top_library)


def test_local_method_is_local_not_backend():
    """client.do_load() should be local, NOT json."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "client.do_load(")
    assert call is not None, "client.do_load(...) not found"
    assert call.top_library != "json", (
        "client.do_load() should NOT be json (it's a local method)")


def test_constructor_local_instance_method_is_local():
    """c.do_load(...) where c=Client() → local."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "c.do_load(")
    assert call is not None, "c.do_load(...) not found"
    assert call.top_library == "local", (
        "c.do_load() should be local, got %s" % call.top_library)


def test_constructor_instance_backend_is_library():
    """c.backend.loads(...) → json."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "c.backend.loads(")
    assert call is not None, "c.backend.loads(...) not found"
    assert call.top_library == "json", (
        "c.backend.loads() should be json, got %s" % call.top_library)
