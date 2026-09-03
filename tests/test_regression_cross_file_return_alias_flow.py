## @package tests.test_regression_cross_file_return_alias_flow
#  Regression coverage for cross-file local aliases in return summaries.

import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "cross_file_return_alias_flow")


def test_cross_file_return_alias_preserves_external_receiver_owner():
    result = analyze_project(FIXTURE)
    calls = [call for call in result.all_api_calls
             if call.expression == "make_array().reshape((1, -1))"]
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"
