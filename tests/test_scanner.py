## @package tests.test_scanner
#  Unit tests for the FileScanner class.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve.scanner import FileScanner, scan_directory


def test_scanner_with_tmp_path(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    (tmp_path / "b.pyi").write_text("def f(): ...")
    (tmp_path / "not_python.txt").write_text("hello")
    (tmp_path / ".hidden.py").write_text("secret")

    scanner = FileScanner()
    results = scanner.scan(str(tmp_path))
    assert any("a.py" in r for r in results)
    assert any("b.pyi" in r for r in results)
    assert not any("not_python.txt" in r for r in results)
    assert not any(".hidden.py" in r for r in results)


def test_scan_files_non_recursive(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.py").write_text("y = 2")

    scanner = FileScanner()
    results = scanner.scan_files(str(tmp_path))
    assert any("a.py" in r for r in results)
    assert not any("b.py" in r for r in results)


def test_scan_dirs(tmp_path):
    sub = tmp_path / "mypkg"
    sub.mkdir()
    (sub / "__init__.py").write_text("")

    scanner = FileScanner()
    dirs = scanner.scan_dirs(str(tmp_path))
    assert any("mypkg" in d for d in dirs)


def test_convenience_function(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    (tmp_path / "b.pyi").write_text("def f(): ...")

    results = scan_directory(str(tmp_path))
    assert len(results) == 2


def test_clear_and_reuse(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    scanner = FileScanner()
    scanner.scan(str(tmp_path))
    assert len(scanner.path) > 0
    scanner.clc()
    assert len(scanner.path) == 0
    assert len(scanner.dirs) == 0


if __name__ == "__main__":
    print("Scanner tests require pytest (tmp_path fixture).")
    print("Run: python -m pytest tests/test_scanner.py -v")
