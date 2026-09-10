from pathlib import Path
from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(name):
    return FlowAnalyzer(project_root=ROOT).analyze(FunctionRef(module='loops', qualname=name))


def test_loop_carried_source_reaches_earlier_call():
    result = run('carried')
    assert any(f['source_parameter'] == 'x' for f in result.calls[0].parameter_flows)
    assert result.trace_parameter('x')['return_paths']
    assert not any(b['reason'] in ('loop_approximation', 'loop_iteration_limit') for b in result.boundaries)
    assert len(result.calls) == 1


def test_break_and_continue_paths():
    result = run('breaks')
    assert result.trace_parameter('y')['return_paths']
    result = run('continued')
    assert not result.trace_parameter('y')['return_paths']


def test_repeated_expression_converges_without_unbounded_evidence():
    result = run('growing')
    paths = result.trace_parameter('x')['return_paths']
    assert paths
    assert max(len(p['evidence']) for p in paths) < 20


def test_projection_growth_stops_with_explicit_limit():
    result = run('projection_growth')
    assert any(b['reason'] == 'loop_iteration_limit' for b in result.boundaries)


def test_fixed_point_does_not_spend_call_budget_per_iteration():
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='loops', qualname='carried'), max_call_contexts=1)
    assert len(result.calls) == 1
    assert any(f['source_parameter'] == 'x' for f in result.calls[0].parameter_flows)
    assert not any(b['reason'] == 'budget_exceeded' for b in result.boundaries)
