## @package tests.test_value_flow_scalar_truth

from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_scalar_truth'


def test_builtin_truth_exports_an_explicit_exact_scalar_precondition():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'convert'))
    call = result.find_calls(callee_name='bool')[0]
    fact = call.implicit_protocol
    assert fact['kind'] == 'builtin_scalar_truth'
    assert fact['precondition']['exact_types'] == ['NoneType', 'bool', 'int', 'float', 'str', 'bytes']
    assert fact['runtime_input_confirmed'] is False
    assert fact['completion'] == 'normal_return_if_precondition'
    assert fact['source_hash'] == result.inputs['sha256'][call.caller.file_path]


@pytest.mark.parametrize('name', ['shadowed', 'invalid', 'expanded', 'rebound'])
def test_unconfirmed_builtin_and_binding_do_not_acquire_scalar_truth(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    assert not result.find_calls(callee_name='bool')[0].implicit_protocol
