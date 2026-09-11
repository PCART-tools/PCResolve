from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_matrix' / 'control'
EDGE_ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(entry):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=3)


def test_next_projects_a_resolved_generators_yielded_value():
    result = run('consumed_generator')
    assert result.trace_parameter('x')['return_paths']
    generated = result.find_calls(callee_name='generate_one')[0]
    assert generated.target.qualname == 'generate_one'
    consumed = result.find_calls(callee_name='next')[0]
    assert consumed.target_status == 'python_protocol'
    assert consumed.return_dependencies[0]['projection'] == ['*']


def test_unconsumed_generator_does_not_apply_body_effects():
    result = run('unconsumed_generator_effect')
    assert not result.trace_parameter('x')['return_paths']
    call = result.find_calls(callee_name='generator_append')[0]
    assert not call.effects


def test_yield_expression_inside_assignment_is_generator_output():
    result = FlowAnalyzer(project_root=EDGE_ROOT).analyze(
        FunctionRef(module='protocols', qualname='consume_assigned_yield'),
        max_depth=3)
    assert result.trace_parameter('value')['return_paths']
