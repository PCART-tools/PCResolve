"""Integration tests: class-scope name resolution through analyze_project()."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve.cross_file import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__),
                       "fixtures", "class_scope_lookup")


def _only_call(result, expression):
    """Return the unique ApiCall whose expression matches exactly."""
    calls = [c for c in result.all_api_calls if c.expression == expression]
    assert len(calls) == 1, \
        f"expected exactly 1 call for {expression!r}, got {len(calls)}: " \
        f"{[(c.expression, c.lineno) for c in calls]}"
    return calls[0]


def test_class_body_own_binding_is_import_backed():
    """class_body_lib = factory() -> requests."""
    result = analyze_project(FIXTURE, scope_model="v2")
    c = _only_call(result, "factory()")
    assert c.top_library == "requests", \
        f"factory() in class body should be requests, got {c.top_library}"


def test_class_body_local_callable_is_local():
    """class_body_local = open('x') -> local."""
    result = analyze_project(FIXTURE, scope_model="v2")
    c = _only_call(result, "open('x')")
    assert c.top_library == "local", \
        f"open('x') in class body D should be local, got {c.top_library}"


def test_method_body_bare_open_is_python():
    """method_bare_builtin = open(path) -> python."""
    result = analyze_project(FIXTURE, scope_model="v2")
    c = _only_call(result, "open(path)")
    assert c.top_library == "python", \
        f"bare open() in method body should be python, got {c.top_library}"


def test_method_body_self_open_is_local():
    """method_self_call = self.open(path) -> local."""
    result = analyze_project(FIXTURE, scope_model="v2")
    c = _only_call(result, "self.open(path)")
    assert c.top_library == "local", \
        f"self.open() should be local, got {c.top_library}"


def test_nested_class_outer_binding_invisible():
    """nested_result = outer_factory() -> unknown."""
    result = analyze_project(FIXTURE, scope_model="v2")
    c = _only_call(result, "outer_factory()")
    assert c.top_library == "unknown", \
        f"outer_factory() in nested class should be unknown, got {c.top_library}"


def test_comprehension_cannot_read_class_namespace():
    """comp_factory() in list comprehension -> unknown."""
    result = analyze_project(FIXTURE, scope_model="v2")
    c = _only_call(result, "comp_factory()")
    assert c.top_library == "unknown", \
        f"comp_factory() in comprehension should be unknown, got {c.top_library}"
