from pathlib import Path
from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(name, parameter_shapes=None):
    return FlowAnalyzer(project_root=ROOT, parameter_shapes=parameter_shapes).analyze(
        FunctionRef(module='protocols', qualname=name))


def test_string_guard_provides_receiver_result_dependency():
    result = run('guarded')
    call = result.find_calls(callee_name='value.split')[0]
    assert call.target_status == 'python_protocol'
    assert result.trace_parameter('value')['return_paths']


def test_unknown_rebound_and_shadowed_receivers_do_not_get_contract():
    for name in ('unknown', 'rebound', 'shadowed'):
        result = run(name)
        assert not result.trace_parameter('value')['return_paths']
        assert result.find_calls(callee_name='value.split')[0].target_status != 'python_protocol'


def test_trusted_parameter_shape_supplies_a_partition_contract():
    contracts = {'protocols.structural_partition': {
        'parameters': {'value': 'str'}, 'provenance': 'reviewed test contract'}}
    result = run('structural_partition', contracts)
    assert result.trace_parameter('value')['return_paths']
    call = result.find_calls(callee_name='value.partition')[0]
    assert call.target_status == 'python_protocol'
    assert result.inputs['parameter_shapes'] == contracts


def test_unpack_shape_alone_does_not_invent_a_receiver_type():
    result = run('structural_partition')
    assert not result.trace_parameter('value')['return_paths']
    assert result.find_calls(callee_name='value.partition')[0].target_status != 'python_protocol'


def test_unconstrained_partition_receiver_remains_unresolved():
    result = run('opaque_partition')
    assert not result.trace_parameter('value')['return_paths']
    assert result.find_calls(callee_name='value.partition')[0].target_status != 'python_protocol'
