from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_matrix' / 'binding'


def test_simple_replacement_decorator_resolves_installed_callable():
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname='decorated_replacement'), max_depth=3)
    assert not result.trace_parameter('x')['return_paths']
    call = result.find_calls(callee_name='replaced_identity')[0]
    assert call.target.module == 'cases'
    assert call.target.qualname == 'replace.replacement'
    assert call.parameter_bindings[0]['parameter'] == 'data'
    assert any(flow['source_parameter'] == 'x'
               and flow['target_parameter'] == 'data'
               for flow in call.parameter_flows)
