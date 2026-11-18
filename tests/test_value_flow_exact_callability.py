## @package tests.test_value_flow_exact_callability

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def analyze(tmp_path, source):
    (tmp_path / 'sample.py').write_text(source, encoding='utf-8')
    return FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'entry'))


def test_builtin_callability_is_conditional_on_an_exact_noncallable_type(tmp_path):
    result = analyze(tmp_path, 'def entry(value):\n    return callable(value)\n')
    call = result.find_calls(callee_name='callable')[0]
    fact = call.implicit_protocol
    assert fact['kind'] == 'builtin_exact_callability'
    assert fact['builtin'] == 'callable'
    assert fact['status'] == 'requires_exact_input'
    assert fact['runtime_input_confirmed'] is False
    assert fact['precondition'] == {'argument': {'position': 0}, 'exact_types': [
        'NoneType', 'bool', 'int', 'float', 'str', 'bytes',
        'dict', 'list', 'tuple', 'set', 'frozenset']}
    assert fact['result'] is False
    assert fact['dependency'] == 'input_object_type_only'
    assert fact['completion'] == 'normal_return_if_precondition'
    assert fact['effects'] == 'none_if_precondition'
    assert fact['source_hash'] == result.inputs['sha256'][call.caller.file_path]
    assert fact['call_id'] == call.id
    assert fact['evidence']['lineno'] == 2
    assert call.target_status == 'python_protocol'
    assert call.target is None
    assert call.binding_status == 'complete'


@pytest.mark.parametrize('source', [
    'def entry(callable, value):\n    return callable(value)\n',
    'def entry(value):\n    callable = other\n    return callable(value)\n',
    'def entry(value):\n    return callable(value)\n    callable = other\n',
    'callable = other\ndef entry(value):\n    return callable(value)\n',
    'if flag:\n    callable = other\ndef entry(value):\n    return callable(value)\n',
    'from other import *\ndef entry(value):\n    return callable(value)\n',
    '__builtins__ = other\ndef entry(value):\n    return callable(value)\n',
    'def entry(value):\n    return callable(value, value)\n',
    'def entry(value):\n    return callable(object=value)\n',
    'def entry(value):\n    return callable(*value)\n',
])
def test_unproven_binding_or_call_shape_does_not_license_callability(tmp_path, source):
    call = analyze(tmp_path, source).find_calls(callee_name='callable')[0]
    assert not call.implicit_protocol
