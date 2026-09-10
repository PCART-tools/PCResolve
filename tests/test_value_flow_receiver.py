from pathlib import Path
import ast
from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(name):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='receiver', qualname=name), max_depth=2)


def test_conditional_excludes_control_dependency():
    result = run('conditional')
    assert not result.trace_parameter('flag')['return_paths']
    assert result.trace_parameter('x')['return_paths'][0]['relation'] == 'direct'


def test_unpack_preserves_projection():
    paths = run('unpack').trace_parameter('values')['return_paths']
    assert paths and paths[0]['projection'] == [1]


def test_loop_preserves_iterable_dependency_with_boundary():
    result = run('loop')
    assert result.trace_parameter('items')['return_paths']
    assert not any(b['reason'] == 'loop_iteration_limit' for b in result.boundaries)


def test_same_class_receiver_binding():
    result = run('Worker.entry')
    call = result.calls[0]
    assert call.target.qualname == 'Worker.identity'
    assert call.receiver_sources[0]['source'] == 'self'
    assert call.parameter_bindings[0]['parameter'] == 'data'
    assert result.trace_parameter('value')['return_paths']


def test_receiver_alias_preserves_lexical_candidate():
    result = run('Worker.alias')
    assert result.calls[0].target.qualname == 'Worker.identity'
    assert result.trace_parameter('value')['return_paths']


def test_mixed_or_changed_receiver_is_not_bound_to_self_class():
    for name in ('Worker.mixed', 'Worker.changed'):
        result = run(name)
        assert result.calls[0].target is None


def test_unanalyzed_calls_still_collected():
    call = run('uncovered').calls[0]
    assert call.callee_name == 'print'
    assert call.analysis_status == 'not_analyzed'


def test_builtin_conversion_has_derived_dependency():
    assert run('converted').trace_parameter('x')['return_paths'][0]['relation'] == 'derived'


def test_literal_unpack_does_not_mix_elements():
    result = run('literal_unpack')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_trace_symbol_call_coverage_and_method_candidates():
    root = Path(__file__).resolve().parents[1] / 'src'
    source = root / 'pcresolve' / 'cross_file.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                  and n.name == 'trace_symbol')
    expected = {(n.lineno, n.col_offset) for n in ast.walk(method) if isinstance(n, ast.Call)}
    result = FlowAnalyzer(project_root=root).analyze(FunctionRef(
        module='pcresolve.cross_file', qualname='ProjectAnalyzer.trace_symbol'))
    assert {(c.lineno, c.col_offset) for c in result.calls} == expected
    recursive = result.find_calls(callee_name='self.trace_symbol')
    assert recursive and all(c.target == result.entry for c in recursive)
    assert not any(b['reason'] in ('unsupported_assignment', 'unsupported_statement') for b in result.boundaries)
