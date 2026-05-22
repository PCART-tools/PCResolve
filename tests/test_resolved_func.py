## @package tests.test_resolved_func
#  Verify resolved_func is computed correctly for various import patterns.

import os
from pcresolve.cross_file import analyze_project

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'resolved_func')


def _get_calls():
    result = analyze_project(FIXTURE)
    return {c.func_name: c for c in result.all_api_calls}


def test_import_alias():
    """import polars as pl; pl.DataFrame(x) -> resolved_func='polars.DataFrame'"""
    calls = _get_calls()
    assert calls["pl.DataFrame"].resolved_func == "polars.DataFrame"


def test_from_import():
    """from polars import DataFrame; DataFrame(x) -> resolved_func='polars.DataFrame'"""
    calls = _get_calls()
    assert calls["DataFrame"].resolved_func == "polars.DataFrame"


def test_from_import_alias():
    """from polars import LazyFrame as LF; LF(x) -> resolved_func='polars.LazyFrame'"""
    calls = _get_calls()
    assert calls["LF"].resolved_func == "polars.LazyFrame"


def test_method_on_result():
    """df = pl.DataFrame(); df.select(x) -> resolved_func='polars.DataFrame.select'"""
    calls = _get_calls()
    assert "df.select" in calls
    assert calls["df.select"].resolved_func == "polars.DataFrame.select"


def test_local_function_no_resolution():
    """def foo(): pass; foo() -> resolved_func='foo' (unchanged)"""
    calls = _get_calls()
    assert calls["foo"].resolved_func == "foo"


def test_pl_col():
    """pl.col(x) -> resolved_func='polars.col'"""
    calls = _get_calls()
    assert calls["pl.col"].resolved_func == "polars.col"
