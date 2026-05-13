## @package tests.test_integration
#  Integration tests using existing fixture projects.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_tests1():
    result = analyze_project(os.path.join(FIXTURES, "tests1"))
    assert len(result.files) == 2
    assert len(result.all_api_calls) == 3
    tops = {c.expression: c.top_library for c in result.all_api_calls}
    assert "requests" in tops.values()
    assert "numpy" in tops.values()


def test_tests2():
    result = analyze_project(os.path.join(FIXTURES, "tests2"))
    assert len(result.files) == 4
    tops = {c.top_library for c in result.all_api_calls}
    assert "requests" in tops
    assert "numpy" in tops
    assert "pandas" in tops


def test_tests3():
    result = analyze_project(os.path.join(FIXTURES, "tests3"))
    assert len(result.files) == 3
    tops = {c.top_library for c in result.all_api_calls}
    assert "requests" in tops or "numpy" in tops


def test_all_files_have_module_names():
    result = analyze_project(os.path.join(FIXTURES, "tests2"))
    for f in result.files:
        assert f.module_name, f"File {f.file_path} has no module name"
        assert f.file_path, f"File has no path"


def test_no_calls_on_empty_project(tmp_path):
    (tmp_path / "empty.py").write_text("x = 1\ny = x + 2")
    result = analyze_project(str(tmp_path))
    assert len(result.files) == 1
    assert len(result.all_api_calls) == 0


if __name__ == "__main__":
    test_tests1()
    test_tests2()
    test_tests3()
    test_all_files_have_module_names()
    print("Integration tests passed.")
    print("Note: test_no_calls_on_empty_project requires pytest tmp_path.")
    print("Run full suite: python -m pytest tests/ -v")
