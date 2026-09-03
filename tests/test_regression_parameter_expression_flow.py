## @package tests.test_regression_parameter_expression_flow
#  Regression coverage for preserving both operands of a parameter expression.

import os

from pcresolve.cross_file import ProjectAnalyzer
from pcresolve.sources import DerivedResult, ParameterSource


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "parameter_expression_flow")


def test_binary_parameter_expression_preserves_both_operands():
    analyzer = ProjectAnalyzer(FIXTURE)
    analyzer.analyze()

    module = analyzer.project_cg.modules["main"]
    edge = next(
        edge for edge in module.edges
        if edge.caller.qualname == "api_1"
        and edge.callee_name == "api_2")
    source = edge.arg_sources["pos"][0]

    assert isinstance(source, DerivedResult)
    assert source.kind == "expression"
    assert source.attribute == "Add"
    assert source.sources == (
        ParameterSource("api_1", "x"),
        ParameterSource("api_1", "y"),
    )


def test_same_library_parameter_expression_receiver_converges():
    analyzer = ProjectAnalyzer(FIXTURE)
    result = analyzer.analyze()

    calls = [call for call in result.all_api_calls
             if call.expression == "(x + y).any()"]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_unresolved_parameter_expression_receiver_stays_unknown():
    analyzer = ProjectAnalyzer(FIXTURE)
    result = analyzer.analyze()

    calls = [call for call in result.all_api_calls
             if call.expression == "(unresolved_x + unresolved_y).any()"]
    assert len(calls) == 1
    assert calls[0].top_library == "unknown"


def test_import_result_and_parameter_expression_converge():
    analyzer = ProjectAnalyzer(FIXTURE)
    result = analyzer.analyze()

    calls = [call for call in result.all_api_calls
             if call.expression == "result.dot(result)"
             and call.lineno == 25]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_import_result_and_conflicting_parameter_stay_unknown():
    analyzer = ProjectAnalyzer(FIXTURE)
    result = analyzer.analyze()

    calls = [call for call in result.all_api_calls
             if call.expression == "result.dot(result)"
             and call.lineno == 30]
    assert len(calls) == 1
    assert calls[0].top_library == "unknown"


def test_same_owner_local_expression_preserves_receiver():
    analyzer = ProjectAnalyzer(FIXTURE)
    result = analyzer.analyze()

    calls = [call for call in result.all_api_calls
             if call.expression == "result.reshape((2, 1))"
             and call.lineno == 36]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_local_expression_with_python_scalar_preserves_receiver():
    analyzer = ProjectAnalyzer(FIXTURE)
    result = analyzer.analyze()

    calls = [call for call in result.all_api_calls
             if call.expression == "result.reshape((2, 1))"
             and call.lineno == 41]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_conflicting_local_expression_owners_stay_unknown():
    analyzer = ProjectAnalyzer(FIXTURE)
    result = analyzer.analyze()

    calls = [call for call in result.all_api_calls
             if call.expression == "result.reshape((2, 1))"
             and call.lineno == 46]
    assert len(calls) == 1
    assert calls[0].top_library == "unknown"
