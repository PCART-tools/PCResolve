## @package tests.test_ownership_contracts
#  Characterization tests for evidence-backed ownership result contracts.

from pcresolve.ownership_contracts import (
    _has_result_owner_contract,
    _is_verified_result_owner,
    _match_attribute_python_shape,
    _match_attribute_result_owner,
    _match_iterator_element_owner,
    _match_iterator_element_shape,
    _match_result_item_owner,
    _match_result_owner,
    _match_result_python_shape,
)
from pcresolve.sources import PythonShape


def test_result_contract_requires_matching_import_backed_prefix():
    assert _match_result_owner("json", "dumps") == "python"
    assert _match_result_owner("json.encoder", "dumps") == "python"
    assert _match_result_owner("myjson", "dumps") is None
    assert _match_result_owner(None, "dumps") is None
    assert _has_result_owner_contract("dumps")
    assert not _has_result_owner_contract("not_a_contract")
    assert _is_verified_result_owner("numpy")
    assert not _is_verified_result_owner("unknown")


def test_attribute_and_call_result_shapes_remain_distinct():
    assert _match_attribute_result_owner("requests", "text") == "python"
    assert _match_attribute_python_shape("requests", "text") == PythonShape("str")
    assert _match_attribute_python_shape("requests", "missing") is None
    assert _match_result_python_shape("re", "split") == PythonShape("list", "str")
    assert _match_result_python_shape("re", "search") is None


def test_iterator_owner_is_not_aggregate_or_item_owner():
    assert _match_iterator_element_owner("glob", "glob") == "python"
    assert _match_iterator_element_shape("glob", "glob") == PythonShape("str")
    assert _match_iterator_element_owner("re", "finditer") == "re"
    assert _match_iterator_element_shape("re", "finditer") is None
    assert _match_result_item_owner("scipy", "svd") == "numpy"
    assert _match_result_owner("scipy", "svd") == "python"
