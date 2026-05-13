## @package tests.test_module_mapper
#  Unit tests for the ModuleMapper class.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve.module_mapper import ModuleMapper


def test_file_to_module_mapping(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "b.py").write_text("y = 2")

    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    modules = mapper.get_all_modules()
    assert "a" in modules
    assert "pkg" in modules
    assert "pkg.b" in modules


def test_module_to_file_mapping(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    sub = tmp_path / "pkg"
    sub.mkdir()
    (sub / "__init__.py").write_text("")
    (sub / "b.py").write_text("y = 2")

    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    file_path = mapper.get_file_path("pkg.b")
    assert file_path.endswith("b.py")


def test_get_module_path(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    all_files = mapper.get_all_files()
    for f in all_files:
        module = mapper.get_module_path(f)
        assert module == "a"


def test_root_init_is_empty(tmp_path):
    (tmp_path / "__init__.py").write_text("")
    (tmp_path / "a.py").write_text("x = 1")

    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    assert "a" in mapper.get_all_modules()


def test_clear(tmp_path):
    (tmp_path / "a.py").write_text("x = 1")
    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()
    assert len(mapper.get_all_modules()) > 0
    mapper.clear()
    assert len(mapper.get_all_modules()) == 0
    assert len(mapper.get_all_files()) == 0


if __name__ == "__main__":
    print("ModuleMapper tests require pytest (tmp_path fixture).")
    print("Run: python -m pytest tests/test_module_mapper.py -v")
