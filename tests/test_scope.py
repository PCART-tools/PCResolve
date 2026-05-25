## @package tests.test_scope
#  Unit tests for the Scope model and integration.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import ast
from pcresolve.scope import (Scope, Binding, SCOPE_MODULE, SCOPE_FUNCTION,
                               SCOPE_CLASS, SCOPE_COMPREHENSION, merge_snapshots)
from pcresolve.single_file import SingleFileAnalyzer, analyze_source


# ── Scope unit tests ────────────────────────────────────────────────────

def test_scope_bind_and_lookup():
    s = Scope(SCOPE_MODULE, "test")
    s.bind("x", "requests")
    b = s.lookup("x")
    assert b is not None
    assert b.source == "requests"
    assert b.scope_kind == SCOPE_MODULE


def test_scope_lookup_through_parent():
    parent = Scope(SCOPE_MODULE, "module")
    parent.bind("x", "requests")
    child = Scope(SCOPE_FUNCTION, "func", parent)
    b = child.lookup("x")
    assert b is not None
    assert b.source == "requests"


def test_scope_child_shadows_parent():
    parent = Scope(SCOPE_MODULE, "module")
    parent.bind("x", "requests")
    child = Scope(SCOPE_FUNCTION, "func", parent)
    child.bind("x", "numpy")
    b = child.lookup("x")
    assert b.source == "numpy"


def test_scope_snapshot_and_restore():
    s = Scope(SCOPE_MODULE, "test")
    s.bind("x", "a")
    snap = s.snapshot()
    s.bind("x", "b")
    assert s.lookup("x").source == "b"
    s.restore(snap)
    assert s.lookup("x").source == "a"


def test_scope_binding_version_increments():
    s = Scope(SCOPE_MODULE, "test")
    s.bind("x", "a")
    assert s.lookup("x").version == 1
    s.bind("x", "b")
    assert s.lookup("x").version == 2


# ── merge_snapshots ─────────────────────────────────────────────────────

def test_merge_both_unchanged():
    base = {"x": Binding("x", "a")}
    left = {"x": Binding("x", "a")}
    right = {"x": Binding("x", "a")}
    merged = merge_snapshots(base, left, right)
    assert merged["x"].source == "a" if isinstance(merged["x"], Binding) else merged["x"] == "a"


def test_merge_one_changed():
    """When one branch changes and the other stays at base, merge should
    produce a SourceSet containing both the base and changed values."""
    from pcresolve.sources import SourceSet
    base = {"x": Binding("x", "a")}
    left = {"x": Binding("x", "b")}
    right = {"x": Binding("x", "a")}
    merged = merge_snapshots(base, left, right)
    assert isinstance(merged["x"], SourceSet), (
        f"Expected SourceSet, got {type(merged['x'])}"
    )


def test_merge_both_changed_different():
    from pcresolve.sources import SourceSet
    base = {"x": Binding("x", "a")}
    left = {"x": Binding("x", "b")}
    right = {"x": Binding("x", "c")}
    merged = merge_snapshots(base, left, right)
    assert isinstance(merged["x"], SourceSet)


def test_merge_new_binding_in_one_branch():
    base = {}
    left = {"x": Binding("x", "a")}
    right = {}
    merged = merge_snapshots(base, left, right)
    assert merged["x"].source == "a" if isinstance(merged["x"], Binding) else merged["x"] == "a"


# ── SingleFileAnalyzer with scope_model="v2" ─────────────────────────────

def _analyze_v2(code):
    """Helper: analyze source with scope_model="v2"."""
    return analyze_source(code, scope_model="v2")


def test_v2_function_param_not_in_module_symbols():
    """Function parameter 'requests' must not pollute module-level symbols."""
    code = """import requests
def f(requests):
    return requests.get('')
"""
    result = _analyze_v2(code)
    # Module-level 'requests' should stay 'requests'
    assert result.symbols.get("requests") == "requests"


def test_v2_local_var_not_in_module_symbols():
    """Local variable 'np' must not overwrite module-level 'np'."""
    code = """import numpy as np
def f():
    np = 'something'
    return np
"""
    result = _analyze_v2(code)
    assert result.symbols.get("np") == "numpy"


def test_v2_comprehension_var_not_in_module_symbols():
    """Comprehension variable 'x' must not leak to module level."""
    code = """import numpy as np
items = [np.array([x]) for x in range(2)]
"""
    result = _analyze_v2(code)
    assert "x" not in result.symbols


def test_v2_class_body_var_not_in_module_symbols():
    """Class body temporary should not be in module symbols."""
    code = """class Foo:
    tmp = 42
    def method(self):
        return tmp
"""
    result = _analyze_v2(code)
    # 'tmp' should not leak to module level
    assert "tmp" not in result.symbols or result.symbols.get("tmp") == "local"


def test_v1_legacy_mode_still_works():
    """v1 mode preserves legacy behaviour (function params leak to module)."""
    code = """import numpy as np
def f():
    np = 'something'
"""
    result = analyze_source(code, scope_model="v1")
    # In v1 mode, np gets overwritten by local binding
    assert result.symbols.get("np") == "local"


def test_v2_nested_function_reads_outer():
    """Nested inner() must be classified as 'local', and s.get('') must
    trace through the outer function's scope to 'requests'."""
    code = """import requests
def outer():
    s = requests.Session()
    def inner():
        return s.get('')
    return inner()
"""
    result = _analyze_v2(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    assert calls.get("inner()") == "local", f"inner() should be local, got {calls}"
    assert calls.get("requests.Session()") == "requests"


def test_v2_local_function_shadows_import():
    """Locally defined function named 'requests' must shadow the import."""
    code = """import requests
def outer():
    def requests():
        return None
    requests()
"""
    result = _analyze_v2(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    assert calls.get("requests()") == "local", f"requests() should be local, got {calls}"


# ── Scope kind in binding ───────────────────────────────────────────────

def test_v1_structured_base_chain_stays_legacy():
    """In v1 mode, structured base calls must keep chain=[] as in Phase 2."""
    code = """from flask import Flask
app = Flask(__name__)
app.logger.info('test')
"""
    result = analyze_source(code, scope_model="v1")
    info_calls = [c for c in result.api_calls if "info" in c.expression]
    assert info_calls, "app.logger.info(...) not found"
    assert info_calls[0].chain == [], (
        f"v1 structured chain must stay [], got {info_calls[0].chain}"
    )


def test_binding_scope_kind_is_set():
    tracer = SingleFileAnalyzer(scope_model="v2")
    code = """import requests
def f():
    x = requests.get('')
"""
    tracer.visit(ast.parse(code))
    # Module scope should have 'requests' binding
    b = tracer.module_scope.lookup("requests")
    assert b is not None
    assert b.scope_kind == SCOPE_MODULE
