## @package tests.test_builtin_ownership_rules
#  Characterization tests for shared ownership builtin policies.

from pcresolve.builtin_ownership import (
    _BUILTIN_CONTAINER_METHODS,
    _builtin_method_return_shape,
    _builtin_shape_type,
    _has_builtin_shape_method,
    _is_builtin,
)
from pcresolve.sources import PythonShape


def test_builtin_names_include_legacy_python_names_without_guessing():
    assert _is_builtin("len")
    assert _is_builtin("xrange")
    assert not _is_builtin("not_a_builtin")
    assert not _is_builtin(None)


def test_shape_methods_require_a_proven_builtin_type():
    assert _builtin_shape_type("NoneType") is type(None)
    assert _builtin_shape_type("list") is list
    assert _builtin_shape_type("not_a_type") is None
    assert _has_builtin_shape_method("list", "append")
    assert not _has_builtin_shape_method("list", "missing")
    assert not _has_builtin_shape_method("unknown", "append")
    assert "append" in _BUILTIN_CONTAINER_METHODS["list"]
    assert "append" not in _BUILTIN_CONTAINER_METHODS["dict"]


def test_method_result_shape_does_not_infer_unknown_receiver():
    assert _builtin_method_return_shape(
        PythonShape("str"), "split") == PythonShape("list", "str")
    assert _builtin_method_return_shape(
        PythonShape("list"), "copy") == PythonShape("list")
    assert _builtin_method_return_shape("unknown", "split") is None
