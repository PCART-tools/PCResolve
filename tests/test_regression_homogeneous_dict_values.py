## @package tests.test_regression_homogeneous_dict_values
#  Regression coverage for dynamic keys over same-owner dictionary values.

import os

import pytest

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "homogeneous_dict_values")


@pytest.fixture(scope="module")
def calls():
    return analyze_project(FIXTURE).all_api_calls


def test_dynamic_dict_key_preserves_uniform_import_owner(calls):
    call = next(
        call for call in calls if call.expression == "selected.run()")
    assert call.top_library == "package_a"


def test_dictionary_values_are_not_reported_as_calls(calls):
    assert [call.expression for call in calls].count("Widget()") == 3


def test_mixed_dictionary_values_do_not_converge_to_one_owner(calls):
    call = next(
        call for call in calls if call.expression == "selected.run()"
        and call.top_library != "package_a")
    assert call.top_library in {"local", "unknown"}
