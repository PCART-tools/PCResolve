import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "field_operator_ownership")


def _calls(result, expression):
    return [
        call
        for file_result in result.files
        for call in file_result.api_calls
        if call.expression == expression
    ]


def test_same_owner_instance_fields_propagate_through_operator_result():
    result = analyze_project(FIXTURE)
    calls = _calls(result, "self.combined.reshape(1)")
    assert len(calls) == 1
    assert calls[0].top_library == "numpy"


def test_parameter_field_does_not_gain_external_owner_from_other_operand():
    result = analyze_project(FIXTURE)
    calls = _calls(result, "self.mixed.reshape(1)")
    assert len(calls) == 1
    assert calls[0].top_library in ("local", "unknown")
