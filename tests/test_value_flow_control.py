from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(name, depth=2):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='control', qualname=name), max_depth=depth)


def test_try_continues_with_derived_parameter():
    result = run('guarded')
    call = result.find_calls(callee_name='convert')[0]
    assert any(f['source_parameter'] == 'x' and f['relation'] == 'derived'
               for f in call.parameter_flows)
    assert call.return_flows
    assert not any(b['reason'] == 'unsupported_statement' for b in result.boundaries)


def test_finally_return_replaces_pending_return():
    result = run('cleanup')
    assert not result.find_calls(callee_name='convert')[0].return_flows
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_exception_uses_prefix_environment_not_completed_body():
    result = run('prefix')
    assert result.trace_parameter('x')['return_paths']
    assert not result.trace_parameter('y')['return_paths']


def test_raise_does_not_execute_else_or_following_assignment():
    result = run('otherwise')
    assert result.trace_parameter('x')['return_paths']
    assert not result.trace_parameter('y')['return_paths']


def test_finally_assignment_changes_normal_exit_environment():
    result = run('final_assignment')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_nested_target_and_capture_are_separate_from_arguments():
    result = run('closure')
    call = result.find_calls(callee_name='inner')[0]
    assert call.target.qualname == 'closure.inner'
    assert call.parameter_bindings[0]['parameter'] == 'data'
    assert call.capture_bindings[0]['capture'] == 'errors'
    assert result.trace_parameter('errors')['return_paths']
    assert not result.trace_parameter('x')['return_paths']


def test_nested_definition_shadows_module_import():
    result = run('lexical')
    assert result.find_calls(callee_name='convert')[0].target.qualname == 'lexical.convert'
    assert result.trace_parameter('x')['return_paths']


def test_call_result_to_argument_is_public_without_opaque_return_guess():
    result = run('opaque')
    first = result.find_calls(callee_name='convert')[0]
    second = result.find_calls(callee_name='external')[0]
    assert second.argument_flows[0]['source'] == first.id
    assert second.argument_flows[0]['kind'] == 'call_result'
    assert not result.trace_parameter('x')['return_paths']


def test_discarded_input_not_forwarded_by_known_callee():
    assert not run('caller').trace_parameter('x')['return_paths']


def test_default_is_evaluated_when_nested_function_is_defined():
    result = run('default_capture')
    assert result.trace_parameter('x')['return_paths']
    assert not result.trace_parameter('y')['return_paths']


def test_known_exception_selects_correct_handler():
    result = run('matched')
    assert result.trace_parameter('x')['return_paths']
    assert not result.trace_parameter('y')['return_paths']


def test_else_only_follows_normal_try_completion():
    result = run('completed_else')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_opt_in_trusted_summary_connects_opaque_result():
    analyzer = FlowAnalyzer(project_root=ROOT, return_summaries={
        'vendor.wrap': {'parameters': ['data'],
                        'returns': [{'parameter': 'data', 'relation': 'contained'}],
                        'provenance': 'test contract v1'}})
    result = analyzer.analyze(FunctionRef(module='control', qualname='wrapped'), max_depth=2)
    paths = result.trace_parameter('x')['return_paths']
    assert paths and paths[0]['relation'] == 'contained'
    assert any(e.get('provenance') == 'test contract v1' for e in paths[0]['evidence'])
    assert not run('wrapped').trace_parameter('x')['return_paths']


def test_uninitialized_nested_function_is_not_a_resolved_target():
    assert run('before_definition').calls[0].target is None


def test_finally_raise_suppresses_return_flow():
    assert not run('finally_raises').find_calls(callee_name='convert')[0].return_flows


def test_local_import_uses_available_definition():
    result = run('local_import')
    assert result.calls[0].target.module == 'helper'
    assert result.trace_parameter('x')['return_paths']


def test_closure_uses_call_time_binding():
    result = run('capture_rebound')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_exception_handler_respects_builtin_hierarchy():
    result = run('exception_hierarchy')
    assert result.trace_parameter('x')['return_paths']
    assert not result.trace_parameter('y')['return_paths']
