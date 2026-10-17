## @package tests.test_value_flow_builtin_length

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def analyze(tmp_path, source):
    (tmp_path / 'sample.py').write_text(source, encoding='utf-8')
    return FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'entry'))


def test_length_protocol_has_an_exact_builtin_input_obligation(tmp_path):
    result = analyze(tmp_path, 'def entry(*args):\n    return len(args)\n')
    call = result.find_calls(callee_name='len')[0]
    fact = call.implicit_protocol
    assert fact['kind'] == 'builtin_container_length'
    assert fact['builtin'] == 'len'
    assert fact['status'] == 'requires_exact_input'
    assert fact['runtime_input_confirmed'] is False
    assert fact['precondition'] == {'argument': {'position': 0},
        'exact_types': ['dict', 'list', 'tuple', 'str', 'bytes', 'set', 'frozenset']}
    assert fact['completion'] == 'normal_return_if_precondition'
    assert fact['effects'] == 'none_if_precondition'
    assert fact['source_hash'] == result.inputs['sha256'][call.caller.file_path]
    assert call.target is None


@pytest.mark.parametrize('source', [
    'def entry(len, *args):\n    return len(args)\n',
    'def entry(*args):\n    len = unknown\n    return len(args)\n',
    'len = replacement\ndef entry(*args):\n    return len(args)\n',
    'def entry(*args):\n    return len(args, args)\n',
    'def entry(*args):\n    return len(object=args)\n',
    'def entry(*args):\n    return len(*args)\n',
])
def test_unconfirmed_length_target_or_binding_has_no_implicit_protocol(tmp_path, source):
    call = analyze(tmp_path, source).find_calls(callee_name='len')[0]
    assert not call.implicit_protocol
