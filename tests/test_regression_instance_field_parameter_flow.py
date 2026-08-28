import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "instance_field_parameter_flow"
)


def _calls():
    result = analyze_project(FIXTURE)
    return {
        (call.lineno, call.expression): call
        for call in result.all_api_calls
    }


def test_same_class_parameter_field_uses_call_edge_owner():
    calls = _calls()
    call = calls[(10, "self.payload.reshape(1, -1)")]
    assert call.top_library == "numpy"


def test_inherited_forwarding_uses_subclass_field_owner():
    calls = _calls()
    call = calls[(18, "self.payload.reshape(1, -1)")]
    assert call.top_library == "numpy"


def test_uncalled_parameter_field_stays_unknown():
    calls = _calls()
    call = calls[(32, "self.payload.reshape(1, -1)")]
    assert call.top_library == "unknown"


def test_derived_field_expression_keeps_defining_class_context():
    calls = _calls()
    call = calls[(40, "(self.payload * 2).sum()")]
    assert call.top_library == "numpy"


def test_same_named_sibling_method_does_not_pollute_field_owner():
    calls = _calls()
    call = calls[(48, "(self.payload * 2).sum()")]
    assert call.top_library == "pandas"


def test_conflicting_subclass_field_owners_stay_unknown():
    calls = _calls()
    call = calls[(53, "self.payload.reshape(1, -1)")]
    assert call.top_library == "unknown"
