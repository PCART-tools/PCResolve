## @package tests.test_regression_parameter_expression_call_flow
#  Regression coverage for expression dataflow across local call edges.

import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "parameter_expression_call_flow")


def test_expression_owner_reaches_nested_local_call_receiver():
    result = analyze_project(FIXTURE)
    calls = [call for call in result.all_api_calls
             if call.expression == "value.reshape((1, -1))"]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_expression_call_edge_retains_both_parameter_sources():
    analyzer_result = analyze_project(FIXTURE)
    calls = [call for call in analyzer_result.all_api_calls
             if call.expression == "value.reshape((1, -1))"]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"
