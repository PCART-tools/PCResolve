## @package tests.test_regression_branch_imports
#  Regression tests: branch imports with multi-value SourceSet after phase 5.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pcresolve import analyze_project
from pcresolve.sources import SourceSet

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "regression_branch_imports")


@pytest.fixture(scope="module")
def result_v1():
    return analyze_project(FIXTURE, scope_model="v1")


@pytest.fixture(scope="module")
def result_v2():
    return analyze_project(FIXTURE, scope_model="v2")


def test_single_file_analyzed_v1(result_v1):
    assert len(result_v1.files) == 1


def test_single_file_analyzed_v2(result_v2):
    assert len(result_v2.files) == 1


def test_lib_array_call_is_pandas_v1(result_v1):
    """v1: last branch wins, so lib -> pandas."""
    lib_calls = [c for c in result_v1.all_api_calls if "lib" in c.expression]
    assert len(lib_calls) == 1
    assert lib_calls[0].top_library == "pandas"


def test_lib_array_call_has_alternatives_v2(result_v2):
    """v2: branch merging produces SourceSet, top should be numpy or pandas."""
    lib_calls = [c for c in result_v2.all_api_calls if "lib" in c.expression]
    assert len(lib_calls) == 1
    assert lib_calls[0].top_library in ("numpy", "pandas")
    assert "SourceSet(" not in str(lib_calls[0].top_library)


def test_branch_imports_no_sourceset_leak(result_v2):
    """No SourceSet repr in library_usage keys or top_library."""
    for call in result_v2.all_api_calls:
        assert "SourceSet(" not in str(call.top_library)
    for lib in result_v2.library_usage:
        assert "SourceSet(" not in str(lib)


def test_if_without_else_merges_with_base():
    """if without else should merge body changes with base as alternatives."""
    code = "import requests as lib\n"
    code += "FLAG = True\n"
    code += "if FLAG:\n"
    code += "    import numpy as lib\n"
    code += "lib.get('https://example.com')\n"

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write(code)
        result = analyze_project(tmpdir, scope_model="v2")
        lib_calls = [c for c in result.all_api_calls if "lib.get" in c.expression]
        assert len(lib_calls) == 1
        assert lib_calls[0].top_library in ("requests", "numpy")
        assert "SourceSet(" not in str(lib_calls[0].top_library)


def test_try_else_inherits_try_bindings():
    """try/else should inherit from try body state, not from pre-try base."""
    code = "try:\n"
    code += "    import numpy as lib\n"
    code += "except Exception:\n"
    code += "    import pandas as lib\n"
    code += "else:\n"
    code += "    value = lib.array([1])\n"
    code += "value.sum()\n"

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write(code)
        result = analyze_project(tmpdir, scope_model="v2")
        lib_calls = [c for c in result.all_api_calls if "lib.array" in c.expression]
        assert len(lib_calls) == 1
        assert lib_calls[0].top_library in ("numpy", "pandas"), \
            f"Expected numpy or pandas, got {lib_calls[0].top_library}"
        sum_calls = [c for c in result.all_api_calls if "sum()" in c.expression]
        assert len(sum_calls) == 1
        assert sum_calls[0].top_library in ("numpy", "pandas"), \
            f"Expected numpy or pandas, got {sum_calls[0].top_library}"


def test_if_without_else_file_symbols_not_local():
    """v2: if-without-else merged symbol should not be 'local' in file symbols."""
    import tempfile
    code = "import requests as lib\n"
    code += "FLAG = True\n"
    code += "if FLAG:\n"
    code += "    import numpy as lib\n"
    code += "lib.get('https://example.com')\n"
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write(code)
        result = analyze_project(tmpdir, scope_model="v2")
        fa = result.files[0]
        assert fa.symbols.get("lib") != "local", \
            f"Expected non-local for lib, got {fa.symbols.get('lib')}"


def test_try_else_symbol_provenance_not_local():
    """try/else: value symbol provenance should not be local."""
    import tempfile
    code = "try:\n"
    code += "    import numpy as lib\n"
    code += "except Exception:\n"
    code += "    import pandas as lib\n"
    code += "else:\n"
    code += "    value = lib.array([1])\n"
    code += "value.sum()\n"
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write(code)
        result = analyze_project(tmpdir, scope_model="v2")
        value_provs = [p for p in result.all_symbol_provenance if p.symbol == "value"]
        assert len(value_provs) >= 1, "Expected symbol provenance for value"
        assert value_provs[0].top_library != "local", \
            f"Expected non-local for value, got {value_provs[0].top_library}"
        assert value_provs[0].top_library in ("numpy", "pandas"), \
            f"Expected numpy or pandas, got {value_provs[0].top_library}"


def test_classification_reason_on_direct_import():
    """Direct import calls should get DIRECT_IMPORT reason with 1.0 confidence."""
    code = "import requests\nrequests.get('https://example.com')\n"
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write(code)
        result = analyze_project(tmpdir, scope_model="v2")
        get_calls = [c for c in result.all_api_calls if "get" in c.expression]
        assert len(get_calls) == 1
        assert get_calls[0].reason == "DIRECT_IMPORT", \
            f"Expected DIRECT_IMPORT, got {get_calls[0].reason}"
        assert get_calls[0].confidence == 1.0


def test_classification_reason_on_branch_merge():
    """Branch-merged calls should get FLOW_MERGE reason with alternatives."""
    result = analyze_project(FIXTURE, scope_model="v2")
    lib_calls = [c for c in result.all_api_calls if "lib" in c.expression]
    assert len(lib_calls) == 1
    assert lib_calls[0].reason == "FLOW_MERGE", \
        f"Expected FLOW_MERGE, got {lib_calls[0].reason}"
    assert len(lib_calls[0].alternatives) == 2, \
        f"Expected 2 alternatives, got {lib_calls[0].alternatives}"
    assert set(lib_calls[0].alternatives) == {"numpy", "pandas"}
    assert lib_calls[0].confidence == 0.5, \
        f"Expected 0.5 for 2 alternatives, got {lib_calls[0].confidence}"


def test_classification_metadata_on_symbol_provenance():
    """Symbol provenance records should carry reason and confidence."""
    code = "import requests\nsession = requests.Session()\n"
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "main.py"), "w") as f:
            f.write(code)
        result = analyze_project(tmpdir, scope_model="v2")
        session_provs = [p for p in result.all_symbol_provenance if p.symbol == "session"]
        assert len(session_provs) >= 1
        assert session_provs[0].reason, "Expected non-empty reason"
        assert session_provs[0].confidence > 0, "Expected positive confidence"
