## @package tests.test_regression_dictionary_key_shapes
#  Dictionary key protocols are independent from stored value ownership.

import pytest

from pcresolve import analyze_project


def _owner(tmp_path, source):
    (tmp_path / 'main.py').write_text(source, encoding='utf-8')
    return next(call.top_library for call in
                analyze_project(str(tmp_path)).all_api_calls
                if call.func_name == 'key.split')


@pytest.mark.parametrize('populate', [
    'items = {"a/b": opaque()}',
    'items = {}\nitems["a/b"] = opaque()',
    'items = {}\nalias = items\nalias["a/b"] = opaque()',
    'items = {}\nfor path in ["a/b", "c/d"]:\n    items[path] = opaque()',
])
def test_string_keys_do_not_inherit_value_owner(tmp_path, populate):
    assert _owner(tmp_path, '''
from dependency import opaque
%s
for key in items:
    key.split("/")
''' % populate) == 'python'


@pytest.mark.parametrize('mutation', [
    'items[opaque()] = "value"',
    'items[42] = "value"',
    'alias = items\nalias[42] = "value"',
    'opaque(items)',
    'items.update(opaque())',
    'items = opaque()',
])
def test_unknown_or_mixed_keys_cannot_claim_string_protocol(tmp_path, mutation):
    assert _owner(tmp_path, '''
from dependency import opaque
items = {"a/b": "value"}
%s
for key in items:
    key.split("/")
''' % mutation) != 'python'


def test_deferred_function_cannot_capture_module_dictionary_keys(tmp_path):
    assert _owner(tmp_path, '''
from dependency import opaque
items = {"a/b": "value"}
def consume():
    for key in items:
        key.split("/")
items[opaque()] = "value"
consume()
''') != 'python'
