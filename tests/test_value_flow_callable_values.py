from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_matrix'


def run(group, entry):
    return FlowAnalyzer(project_root=ROOT / group).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=3)


def test_imported_callable_survives_local_alias_assignment():
    result = run('binding', 'local_alias')
    assert result.trace_parameter('x')['return_paths']
    call = result.find_calls(callee_name='chosen')[0]
    assert call.target.module == 'helpers'
    assert call.target.qualname == 'identity'
    assert call.parameter_bindings[0]['parameter'] == 'data'


def test_lambda_value_has_a_local_callable_summary():
    result = run('control', 'lambda_call')
    assert result.trace_parameter('x')['return_paths']
    call = result.find_calls(callee_name='apply')[0]
    assert call.target.module == 'cases'
    assert '<lambda>@' in call.target.qualname
    assert call.parameter_bindings[0]['parameter'] == 'value'
