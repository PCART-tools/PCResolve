from pathlib import Path
from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(name, depth=2):
    return FlowAnalyzer(project_root=ROOT).analyze(FunctionRef(module='recursive', qualname=name), max_depth=depth)


def test_recursive_parameter_rotation_reaches_fixed_point():
    result = run('rotate')
    for name in ('a', 'b', 'c'):
        trace = result.trace_parameter(name)
        assert trace['return_paths'], name
        assert trace['summary_status'] == 'converged'
    assert not result.trace_parameter('stop')['return_paths']


def test_recursion_without_base_return_does_not_invent_flow():
    assert not run('no_return').trace_parameter('a')['return_paths']


def test_nested_container_projection_across_calls():
    result = run('select', depth=3)
    assert result.trace_parameter('b')['return_paths']
    assert not result.trace_parameter('a')['return_paths']


def test_recursive_container_growth_reports_summary_limit():
    result = run('growing')
    trace = result.trace_parameter('value')
    assert trace['return_paths']
    assert trace['summary_status'] == 'bounded'
    assert trace['summary_iterations'] == 32
    assert any(b['reason'] == 'return_summary_limit' for b in trace['boundaries'])
    assert not any(b['reason'] == 'return_summary_limit' for b in result.boundaries)
