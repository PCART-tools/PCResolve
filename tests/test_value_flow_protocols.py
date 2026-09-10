from pathlib import Path
from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(name):
    return FlowAnalyzer(project_root=ROOT).analyze(FunctionRef(module='protocols', qualname=name))


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
