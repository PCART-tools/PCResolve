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


def test_resolve_module_name_simple_sibling(tmp_path):
    """import data in ex_4_2.main → resolves to ex_4_2.data."""
    sub = tmp_path / "ex_4_2"
    sub.mkdir(parents=True)
    (sub / "main.py").write_text("import data")
    (sub / "data.py").write_text("x = 1")

    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    resolved = mapper.resolve_module_name("data", "ex_4_2.main")
    assert resolved == "ex_4_2.data"


def test_resolve_module_name_already_dotted(tmp_path):
    """Already-dotted names are returned as-is."""
    sub = tmp_path / "pkg"
    sub.mkdir(parents=True)
    (sub / "__init__.py").write_text("")
    (sub / "mod.py").write_text("x = 1")

    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    resolved = mapper.resolve_module_name("pkg.mod", "pkg.main")
    assert resolved == "pkg.mod"


def test_resolve_module_name_top_level(tmp_path):
    """Top-level module is found without context."""
    (tmp_path / "topmod.py").write_text("x = 1")

    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    resolved = mapper.resolve_module_name("topmod", None)
    assert resolved == "topmod"


def test_resolve_module_name_not_found(tmp_path):
    """Unresolvable name is returned as-is."""
    sub = tmp_path / "pkg"
    sub.mkdir(parents=True)
    (sub / "main.py").write_text("import something")

    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    resolved = mapper.resolve_module_name("something", "pkg.main")
    assert resolved == "something"


def test_resolve_module_name_nested_package(tmp_path):
    """import mod in pkg.sub.main → resolves to pkg.sub.mod."""
    sub = tmp_path / "pkg" / "sub"
    sub.mkdir(parents=True)
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "sub" / "__init__.py").write_text("")
    (sub / "main.py").write_text("import mod")
    (sub / "mod.py").write_text("x = 1")

    mapper = ModuleMapper(str(tmp_path))
    mapper.scan_project()

    resolved = mapper.resolve_module_name("mod", "pkg.sub.main")
    assert resolved == "pkg.sub.mod"


if __name__ == "__main__":
    print("ModuleMapper tests require pytest (tmp_path fixture).")
    print("Run: python -m pytest tests/test_module_mapper.py -v")
