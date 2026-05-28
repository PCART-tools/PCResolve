## @package tests.test_regression_multiple_returns
#  Regression tests: multiple return paths lock current behaviour.
#  After phase 5, make() return source should be SourceSet([requests, numpy]).

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pcresolve import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "regression_multiple_returns")


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


def test_single_file_analyzed(result):
    assert len(result.files) == 1


def test_value_get_call_exists(result):
    """value.get(...) call should exist in the output."""
    exprs = [c.expression for c in result.all_api_calls]
    assert any("get" in e for e in exprs)


def test_make_return_call_classified(result):
    """make(True) itself is a local function call."""
    local_calls = [c for c in result.all_api_calls if c.top_library == "local"]
    assert len(local_calls) >= 1
    exprs = [c.expression for c in local_calls]
    assert any("make" in e for e in exprs)


def test_value_get_has_multi_source(result):
    """UPDATEPHASE5: value.get(...) traces to either requests or numpy.
    Full alternatives support needs classification engine (Phase 8A)."""
    value_calls = [c for c in result.all_api_calls if "get" in c.expression]
    assert len(value_calls) == 1
    assert value_calls[0].top_library in ("requests", "numpy")


def test_return_sources_is_sourceset():
    """SingleFileAnalyzer must produce a SourceSet for make() with two returns."""
    import ast
    from pcresolve.single_file import SingleFileAnalyzer
    from pcresolve.sources import SourceSet
    code = "import requests\nimport numpy as np\n"
    code += "def make(flag):\n"
    code += "    if flag:\n        return requests.Session()\n"
    code += "    return np.array([1])\n"
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    rs = tracer.return_sources.get("make")
    assert isinstance(rs, SourceSet), f"Expected SourceSet, got {type(rs)}: {rs}"
    displays = []
    from pcresolve.sources import source_display
    for src in rs.sources:
        displays.append(source_display(src))
    assert any("Session" in d for d in displays), displays
    assert any("array" in d for d in displays), displays


def test_chained_call_through_return():
    """make(True).get() must resolve through SourceSet return_sources."""
    import ast
    from pcresolve.single_file import SingleFileAnalyzer
    code = "import requests\nimport numpy as np\n"
    code += "def make(flag):\n"
    code += "    if flag:\n        return requests.Session()\n"
    code += "    return np.array([1])\n"
    code += "make(True).get('https://example.com')\n"
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    calls = {c['api']: c['top'] for c in tracer.api_calls if 'get' in c['api']}
    assert calls, "make().get() call not found"
    get_call = list(calls.values())[0]
    assert "local" not in str(get_call).lower(), f"Expected not local, got {get_call}"


def test_value_get_top_library_v2():
    """value.get(...) must resolve to requests or numpy in v2 (regression check)."""
    result_v2 = analyze_project(FIXTURE, scope_model="v2")
    value_calls = [c for c in result_v2.all_api_calls if "get" in c.expression]
    assert len(value_calls) == 1
    assert value_calls[0].top_library in ("requests", "numpy"), \
        f"Expected requests or numpy, got {value_calls[0].top_library}"


def test_no_sourceset_leak_in_top_library():
    """No SourceSet dataclass repr must leak into top_library or library_usage keys."""
    for scope_model in ("v1", "v2"):
        result = analyze_project(FIXTURE, scope_model=scope_model)
        for call in result.all_api_calls:
            assert "SourceSet(" not in str(call.top_library), \
                f"[{scope_model}] Leaked SourceSet in top_library: {call.top_library}"
        for lib in result.library_usage:
            assert "SourceSet(" not in str(lib), \
                f"[{scope_model}] Leaked SourceSet in library_usage key: {lib}"


@pytest.mark.xfail(reason="7B-full P2: multi-return SourceSet convergence", strict=True)
def test_make_chained_call_project_level():
    """make(True).get() at project level must resolve to requests or numpy."""
    code = "import requests\nimport numpy as np\n"
    code += "def make(flag):\n"
    code += "    if flag:\n        return requests.Session()\n"
    code += "    return np.array([1])\n"
    code += "make(True).get('https://example.com')\n"

    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write(code)
        for scope_model in ("v1", "v2"):
            result = analyze_project(tmpdir, scope_model=scope_model)
            get_calls = [c for c in result.all_api_calls if "get" in c.expression]
            assert len(get_calls) == 1, f"[{scope_model}] Expected 1 get call, got {len(get_calls)}"
            assert get_calls[0].top_library in ("requests", "numpy"), \
                f"[{scope_model}] Expected requests or numpy, got {get_calls[0].top_library}"


def test_mixed_local_and_third_party_return():
    """SourceSet with local class + third-party must prefer the third-party top."""
    code = "import requests\n"
    code += "class Local:\n    pass\n"
    code += "def make(flag):\n"
    code += "    if flag:\n        return Local()\n"
    code += "    return requests.Session()\n"
    code += "make(False).get('https://example.com')\n"

    import tempfile
    import os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write(code)
        for scope_model in ("v1", "v2"):
            result = analyze_project(tmpdir, scope_model=scope_model)
            get_calls = [c for c in result.all_api_calls if "get" in c.expression]
            assert len(get_calls) == 1, f"[{scope_model}] Expected 1 get call, got {len(get_calls)}"
            assert get_calls[0].top_library == "requests", \
                f"[{scope_model}] Expected requests, got {get_calls[0].top_library}"
            assert "SourceSet(" not in str(get_calls[0].top_library), \
                f"[{scope_model}] Leaked SourceSet in top_library"
            assert "requests" in result.library_usage, \
                f"[{scope_model}] requests missing from library_usage"
