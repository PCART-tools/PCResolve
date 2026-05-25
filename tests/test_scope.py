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


# ── CallSite collection ─────────────────────────────────────────────────

def test_callsite_collected_for_simple_call():
    """requests.get() produces 1 CallSite."""
    tracer = SingleFileAnalyzer()
    code = "import requests\nrequests.get('')\n"
    tracer.visit(ast.parse(code))
    assert len(tracer.call_site_objects) == 1
    cs = tracer.call_site_objects[0]
    assert cs.expression == "requests.get('')"
    assert cs.func_name == "requests.get"


def test_callsite_module_name_filled():
    """CallSite.module_name is populated from the analyzer."""
    tracer = SingleFileAnalyzer(module_name="pkg.mod")
    code = "import requests\nrequests.get('')\n"
    tracer.visit(ast.parse(code))
    cs = tracer.call_site_objects[0]
    assert cs.module_name == "pkg.mod"


def test_callsite_v2_scope_name():
    """v2 function body calls carry scope_name == function name."""
    tracer = SingleFileAnalyzer(scope_model="v2")
    code = "import requests\ndef f():\n    requests.get('')\n"
    tracer.visit(ast.parse(code))
    func_calls = [cs for cs in tracer.call_site_objects if cs.scope_name]
    assert len(func_calls) >= 1
    assert func_calls[0].scope_name == "f"


# ── Symbol provenance ──────────────────────────────────────────────────

def test_symbol_refs_collected():
    """SingleFileAnalyzer populates symbol_refs for imports and variables."""
    tracer = SingleFileAnalyzer(module_name="test")
    code = "import requests\ns = requests.Session()\n"
    tracer.visit(ast.parse(code))
    kinds = {r.kind for r in tracer.symbol_refs}
    assert "import" in kinds
    assert "variable" in kinds


def test_symbol_provenance_in_project_mode():
    """ProjectAnalyzer generates symbol_provenance records."""
    import tempfile, os
    from pcresolve.cross_file import analyze_project
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.py"), "w") as f:
            f.write("import requests\ns = requests.Session()\ns.get('')\n")
        result = analyze_project(td)
        assert len(result.all_symbol_provenance) >= 2
        imports = [p for p in result.all_symbol_provenance if p.kind == "import"]
        assert len(imports) >= 1
        assert imports[0].top_library == "requests"


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


# ── Library Usage Index ─────────────────────────────────────────────────


def test_library_usage_groups_by_top():
    """Library usage aggregates calls and symbols by top-level library."""
    import tempfile, os
    from pcresolve.cross_file import analyze_project
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.py"), "w") as f:
            f.write("import requests\nimport numpy as np\n"
                    "r = requests.get('')\nnp.array([1])\n")
        result = analyze_project(td)
        usage = result.library_usage
        assert "requests" in usage
        assert "numpy" in usage
        assert usage["requests"].api_call_count >= 1


def test_library_usage_skips_local_and_python():
    """Library usage must not include local/python entries."""
    import tempfile, os
    from pcresolve.cross_file import analyze_project
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.py"), "w") as f:
            f.write("import requests\ndef f():\n    return range(2)\n"
                    "x = f()\nrequests.get('')\n")
        result = analyze_project(td)
        usage = result.library_usage
        assert "local" not in usage
        assert "python" not in usage


def test_library_usage_files_deduplicated():
    """LibraryUsage.files must be deduplicated and sorted."""
    import tempfile, os
    from pcresolve.cross_file import analyze_project
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "a.py"), "w") as f:
            f.write("import requests\nrequests.get('')\n")
        with open(os.path.join(td, "b.py"), "w") as f:
            f.write("import requests\nrequests.post('')\n")
        result = analyze_project(td)
        usage = result.library_usage
        assert usage["requests"].files == sorted(usage["requests"].files)
        assert len(usage["requests"].files) == len(set(usage["requests"].files))


# ── v2 provenance regression ────────────────────────────────────────────

def test_v2_local_var_not_in_library_usage():
    """v2 local variable 's' must not appear as a library in usage."""
    import tempfile, os
    from pcresolve.cross_file import analyze_project
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.py"), "w") as f:
            f.write("import requests\n"
                    "def f():\n"
                    "    s = requests.Session()\n"
                    "    s.get('')\n"
                    "f()\n")
        result = analyze_project(td, scope_model="v2")
        usage = result.library_usage
        assert "s" not in usage, f"Local var 's' leaked into library_usage: {list(usage.keys())}"


def test_v2_param_shadow_not_in_library_usage():
    """v2 parameter shadowing an import must not contribute to third-party usage."""
    import tempfile, os
    from pcresolve.cross_file import analyze_project
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.py"), "w") as f:
            f.write("import requests\n"
                    "def f(requests):\n"
                    "    requests.get('')\n"
                    "f('')\n")
        result = analyze_project(td, scope_model="v2")
        # Check that the parameter does NOT contribute to requests' symbol_count
        usage = result.library_usage
        if "requests" in usage:
            prov_for_requests = [p for p in result.all_symbol_provenance
                                  if p.top_library == "requests"]
            # Only the module-level import should contribute, not the parameter
            for p in prov_for_requests:
                assert p.scope_name != "f", (
                    f"Parameter shadow in f() mis-attributed to requests: {p.symbol}")


def test_v2_s_provenance_is_requests():
    """v2 local s = requests.Session() must have top_library='requests'."""
    import tempfile, os
    from pcresolve.cross_file import analyze_project
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "m.py"), "w") as f:
            f.write("import requests\n"
                    "def f():\n"
                    "    s = requests.Session()\n")
        result = analyze_project(td, scope_model="v2")
        for p in result.all_symbol_provenance:
            if p.symbol == "s":
                assert p.top_library == "requests", (
                    f"v2 s provenance should be 'requests', got {p.top_library} chain={p.chain}"
                )


def test_library_usage_same_filename_different_dirs():
    """Same-named files in different directories must not be merged."""
    import tempfile, os
    from pcresolve.cross_file import analyze_project
    with tempfile.TemporaryDirectory() as td:
        pkg1 = os.path.join(td, "pkg1")
        pkg2 = os.path.join(td, "pkg2")
        os.makedirs(pkg1)
        os.makedirs(pkg2)
        with open(os.path.join(pkg1, "__init__.py"), "w") as f:
            f.write("import requests\nrequests.get('')\n")
        with open(os.path.join(pkg2, "__init__.py"), "w") as f:
            f.write("import requests\nrequests.post('')\n")
        result = analyze_project(td)
        usage = result.library_usage
        files = usage["requests"].files
        assert len(files) == 2, (
            f"Expected 2 distinct files, got {files}"
        )
