## @package tests.test_cross_file_call_result_resolution
#  Characterize CallResult source resolution before extracting its branch.

from pcresolve.cross_file import ProjectAnalyzer
from pcresolve.sources import (
    CallResult,
    DerivedResult,
    InstanceMethod,
    PythonShape,
    UnknownSource,
)


def test_explicit_call_result_sources_keep_owner_and_display(tmp_path):
    analyzer = ProjectAnalyzer(str(tmp_path))
    cases = (
        (CallResult("make", display_name="factory.make",
                    result_source=UnknownSource("dynamic")),
         ("factory.make()", "main", "unknown")),
        (CallResult("str", result_source=PythonShape("str")),
         ("str()", "main", "python")),
        (CallResult("load", result_source="requests"),
         ("load()", "main", "requests")),
        (CallResult("next", result_source=DerivedResult("iterator", ())),
         ("next()", "main", "unknown")),
    )

    for source, expected in cases:
        assert analyzer._resolve_structured_source("main", source, {}) == expected


def test_parameter_method_result_stays_unknown_without_explicit_source(tmp_path):
    analyzer = ProjectAnalyzer(str(tmp_path))
    callee = InstanceMethod("arg", "build", parameter_scope="f",
                            parameter_name="arg")
    source = CallResult(callee)

    assert analyzer._resolve_structured_source("main", source, {}) == (
        "%s()" % callee, "main", "unknown")
