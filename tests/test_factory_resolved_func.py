## @package tests.test_factory_resolved_func
#  Verify factory-return calls preserve the factory's full import path.

import os

from pcresolve.cross_file import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "factory_resolved_func")
AMBIGUOUS_FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "ambiguous_factory_resolved_func")


def _calls_by_name():
    """Return analyzed calls grouped by function name."""
    result = analyze_project(FIXTURE)
    return {call.func_name: call for call in result.all_api_calls}


def test_from_import_factory_return_preserves_full_path():
    """A call on a generated model resolves to pydantic.create_model."""
    call = _calls_by_name()["DynamicModel"]

    assert call.reason == "RETURN_PROPAGATION"
    assert call.top_library == "pydantic"
    assert call.resolved_func == "pydantic.create_model"


def test_aliased_factory_return_preserves_original_import_name():
    """Factory aliases resolve to the imported factory's original name."""
    call = _calls_by_name()["AliasedModel"]

    assert call.reason == "RETURN_PROPAGATION"
    assert call.top_library == "pydantic"
    assert call.resolved_func == "pydantic.create_model"


def test_qualified_factory_return_preserves_full_path():
    """A qualified factory call stays fully qualified after propagation."""
    call = _calls_by_name()["QualifiedModel"]

    assert call.reason == "RETURN_PROPAGATION"
    assert call.top_library == "pydantic"
    assert call.resolved_func == "pydantic.create_model"


def test_ambiguous_factory_return_is_not_bound_to_one_candidate():
    """Same-owner candidate factories do not produce a guessed API path."""
    result = analyze_project(AMBIGUOUS_FIXTURE)
    call = next(
        item for item in result.all_api_calls
        if item.func_name == "DynamicModel")

    assert call.reason == "RETURN_PROPAGATION"
    assert call.top_library == "pydantic"
    assert call.resolved_func == "pydantic"
