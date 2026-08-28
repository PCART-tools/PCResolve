## @package tests.test_regression_local_classmethod_factory
#  Regression coverage for local class methods returning local instances.

import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "local_classmethod_factory"
)


def test_local_classmethod_return_preserves_local_receiver_identity():
    result = analyze_project(FIXTURE)
    calls = {
        call.expression: call
        for call in result.all_api_calls
    }

    assert calls["value.local_method()"].top_library == "local"


def test_local_classmethod_call_remains_local():
    result = analyze_project(FIXTURE)
    calls = {
        call.expression: call
        for call in result.all_api_calls
    }

    assert calls["LocalValue.make()"].top_library == "local"


def test_ambiguous_local_classmethod_return_is_unknown():
    result = analyze_project(FIXTURE)
    calls = {
        call.expression: call
        for call in result.all_api_calls
    }

    assert calls["ambiguous.value()"].top_library == "unknown"
