import copy
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures/value_flow_with_exit'


def analyze(name, analyzer=None):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='cases', qualname=name), max_depth=3)


def exits(result):
    return [call for call in result.calls if call.implicit_protocol.get('method') == '__exit__']


def test_normal_exit_has_an_implicit_call_and_empty_exception_triple():
    result = analyze('normal')
    call = exits(result)[0]
    assert call.target.qualname == 'Noop.__exit__'
    assert call.binding_status == 'complete'
    assert call.implicit_protocol['incoming_exit']['kind'] == 'normal'
    assert call.implicit_protocol['incoming_exit']['exception'] is None
    assert call.implicit_protocol['runtime_target_confirmed'] is False
    assert len(call.argument_sources) == 4
    assert all(argument.get('literal', {}).get('value') is None for argument in call.argument_sources[1:])
    assert ':with_exit:' in call.id


@pytest.mark.parametrize('name,analyzed', [('suppress_raise', True), ('propagate_raise', False)])
def test_known_exit_truth_controls_only_the_exception_path(name, analyzed):
    result = analyze(name)
    assert (result.find_calls(callee_name='fixed')[0].analysis_status == 'analyzed') is analyzed
    call = next(call for call in exits(result) if call.implicit_protocol['incoming_exit']['kind'] == 'raise')
    assert call.implicit_protocol['incoming_exit']['exception'] == 'ValueError'
    expected = 'normal' if analyzed else 'raise'
    assert call.implicit_protocol['exit_outcomes'] == [{'kind': expected,
        'exception': None if analyzed else 'ValueError'}]
    assert not any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)


def test_unknown_truth_keeps_suppressed_propagated_and_truth_protocol_boundaries():
    result = analyze('unknown_truth')
    assert result.find_calls(callee_name='fixed')[0].analysis_status == 'analyzed'
    assert any(boundary['reason'] == 'context_exit_truth_unresolved' for boundary in result.boundaries)


@pytest.mark.parametrize('name,has_kwargs', [('pending_return', False), ('pending_copy', True),
                                           ('pending_rebind', True), ('normal_sensitive', False)])
def test_pending_return_uses_selected_identity_and_post_exit_contents(name, has_kwargs):
    result = analyze(name)
    assert bool(result.trace_parameter('kwargs')['return_paths']) is has_kwargs
    assert exits(result)
    assert any(call.implicit_protocol.get('pending_return_sources') for call in exits(result))
    assert not any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)


@pytest.mark.parametrize('name', ['reverse_order', 'nested_order'])
def test_cleanup_reverses_successful_entry_order_and_mutates_shared_object(name):
    result = analyze(name)
    assert not result.trace_parameter('kwargs')['return_paths']
    assert result.trace_parameter('value')['return_paths']
    calls = [call for call in exits(result) if call.implicit_protocol['incoming_exit']['kind'] == 'return']
    assert [call.target.qualname.rsplit('.', 2)[-2] for call in sorted(
        calls, key=lambda call: call.implicit_protocol['cleanup_order'])] == ['Clear', 'Restore']


def test_failure_of_later_enter_cleans_only_successfully_entered_managers():
    result = analyze('later_enter_failure')
    assert result.find_calls(callee_name='unreachable')[0].analysis_status == 'not_analyzed'
    assert result.find_calls(callee_name='fixed')[0].analysis_status == 'analyzed'
    assert exits(result) and all(call.target.qualname != 'FailEnter.__exit__' for call in exits(result))
    assert any(call.implicit_protocol['incoming_exit'].get('origin') == 'context_enter' for call in exits(result))


def test_possible_later_context_expression_failure_still_cleans_the_prefix():
    result = analyze('later_expression_failure')
    calls = [call for call in exits(result)
             if call.implicit_protocol['incoming_exit'].get('origin') == 'context_expression']
    assert calls and all(call.implicit_protocol['item_index'] == 0 for call in calls)


def test_raising_exit_replaces_pending_return_and_reaches_matching_handler():
    result = analyze('exit_replaces_return')
    assert not result.trace_parameter('kwargs')['return_paths']
    assert any(call.implicit_protocol['incoming_exit']['kind'] == 'return' for call in exits(result))


def test_outer_exit_sees_exception_replacing_inner_pending_return():
    result = analyze('outer_suppresses_exit_raise')
    assert result.find_calls(callee_name='fixed')[0].analysis_status == 'analyzed'
    assert any(call.target.qualname == 'Suppress.__exit__'
               and call.implicit_protocol['incoming_exit']['exception'] == 'RuntimeError' for call in exits(result))


def test_true_exit_result_does_not_cancel_pending_return():
    result = analyze('true_does_not_cancel_return')
    assert result.trace_parameter('kwargs')['return_paths']
    assert result.find_calls(callee_name='unreachable')[0].analysis_status == 'not_analyzed'
    assert any(call.implicit_protocol['incoming_exit']['kind'] == 'return' for call in exits(result))


@pytest.mark.parametrize('name,kind', [('break_exit', 'break'), ('continue_exit', 'continue')])
def test_loop_control_runs_cleanup_with_empty_exception_state(name, kind):
    result = analyze(name)
    assert any(call.implicit_protocol['incoming_exit']['kind'] == kind
               and call.implicit_protocol['incoming_exit']['exception'] is None for call in exits(result))
    assert any(effect.get('operation') == 'clear' for call in exits(result)
               if call.implicit_protocol['incoming_exit']['kind'] == kind for effect in call.effects)
    if name == 'continue_exit':
        assert result.find_calls(callee_name='unreachable')[0].analysis_status == 'not_analyzed'


def test_exit_uses_saved_manager_not_rebound_context_or_as_variable():
    result = analyze('saved_manager')
    assert exits(result) and all(call.target.qualname == 'Noop.__exit__' for call in exits(result))
    allocated = result.find_calls(callee_name='Noop')[0]
    assert all(call.receiver_sources[0]['source'] == allocated.id for call in exits(result))


def test_exception_branch_selection_does_not_apply_normal_exit_only_mutation():
    assert analyze('exception_sensitive').trace_parameter('kwargs')['return_paths']


def test_exit_finite_pop_preserves_open_tail_and_reports_key_effect():
    result = analyze('finite_pop')
    paths = result.trace_parameter('kwargs')['return_paths']
    assert paths and any(['out'] in path.get('excluded_paths', []) for path in paths)
    assert any(effect.get('element_path') == ['out'] for call in exits(result) for effect in call.effects)


def test_required_key_pop_retains_a_possible_exception_completion():
    result = analyze('exit_pop_raises')
    assert any(boundary['reason'] == 'context_exit_exception_path' for boundary in result.boundaries)
    assert exits(result)


def test_unknown_exit_keeps_boundary_and_cannot_be_called_effect_free():
    result = analyze('unknown_exit')
    assert exits(result)
    assert any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)


def test_repeated_analysis_and_expansion_do_not_reuse_exit_objects_or_mutate_snapshot():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyze('reverse_order', analyzer)
    before = copy.deepcopy(result.to_dict())
    analyze('unknown_exit', analyzer)
    assert analyze('reverse_order', analyzer).to_dict() == before
    expanded = analyzer.expand(result, exits(result)[0].id)
    assert result.to_dict() == before and expanded.to_dict()['entry'] == before['entry']


@pytest.mark.parametrize('name', ['caught_pop_failure', 'caught_delete_failure', 'popped_exit_result'])
def test_required_key_failure_keeps_pre_operation_contents_and_return_pop_can_raise(name):
    result = analyze(name)
    paths = result.trace_parameter('kwargs')['return_paths']
    assert paths and any(['out'] not in path.get('excluded_paths', []) for path in paths)
    if name == 'popped_exit_result':
        assert any(boundary['reason'] == 'context_exit_exception_path' for boundary in result.boundaries)


def test_unknown_truth_protocol_invalidates_previous_strong_contents():
    result = analyze('unknown_truth_mutation')
    assert any(boundary['reason'] == 'context_exit_truth_unresolved' for boundary in result.boundaries)
    assert all(['out'] not in path.get('excluded_paths', [])
               for path in result.trace_parameter('kwargs')['return_paths'])


def test_exit_result_is_not_truth_tested_on_normal_return():
    result = analyze('normal_unknown_truth')
    assert result.trace_parameter('kwargs')['return_paths']
    assert not any(boundary['reason'] in ('context_exit_truth_unresolved', 'context_exit_unmodeled')
                   for boundary in result.boundaries)


@pytest.mark.parametrize('name', ['dynamic_key', 'unknown_attribute', 'partial_unknown'])
def test_unknown_protocol_or_effect_cannot_publish_a_complete_exit_summary(name):
    result = analyze(name)
    assert any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)
    assert all(['out'] not in path.get('excluded_paths', [])
               for path in result.trace_parameter('kwargs')['return_paths'])


def test_exit_recursion_and_budget_keep_explicit_boundaries():
    assert any(boundary['reason'] == 'context_exit_recursion'
               for boundary in analyze('recursive_exit').boundaries)
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname='normal'), max_call_contexts=10)
    assert any(boundary['reason'] == 'context_exit_budget' for boundary in result.boundaries)


def test_cleanup_path_budget_is_bounded_without_dropping_pending_return():
    result = analyze('many_exits')
    assert any(boundary['reason'] == 'context_exit_path_budget' for boundary in result.boundaries)
    assert result.trace_parameter('kwargs')['return_paths']
    assert len(exits(result)) < 500


def test_pending_return_expression_is_evaluated_once():
    result = analyze('return_once')
    call = result.find_calls(callee_name='kwargs.pop')[0]
    assert len([call for call in result.calls if call.callee_name == 'kwargs.pop']) == 1
    assert any(dependency.get('projection') == ['out'] for dependency in call.return_dependencies)
    assert not any(value.get('container_object') for value in call.result_sources)
    assert any(call.implicit_protocol['incoming_exit']['kind'] == 'return' for call in exits(result))


def test_literal_alias_truth_and_finally_effects_are_modeled():
    assert analyze('literal_truth_alias').find_calls(callee_name='fixed')[0].analysis_status == 'analyzed'
    result = analyze('final_exit')
    assert not result.trace_parameter('kwargs')['return_paths']
    assert not any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)


@pytest.mark.parametrize('name', ['unknown_hash', 'unknown_iteration', 'unmodeled_instance_field'])
def test_unproved_data_protocols_and_heap_field_aliases_remain_boundaries(name):
    assert any(boundary['reason'] == 'context_exit_unmodeled' for boundary in analyze(name).boundaries)


def test_closure_capture_is_read_at_exit_time_not_manager_construction():
    assert analyze('captured_default_rebinding').trace_parameter('kwargs')['return_paths']


def test_unknown_enter_failure_does_not_preserve_previous_strong_key_exclusion():
    result = analyze('failing_enter_changes_state')
    assert all(['out'] not in path.get('excluded_paths', [])
               for path in result.trace_parameter('kwargs')['return_paths'])
    assert result.find_calls(callee_name='unreachable')[0].analysis_status == 'not_analyzed'


def test_exit_local_alias_mutates_the_same_captured_dict():
    result = analyze('alias_pop')
    assert result.trace_parameter('kwargs')['return_paths']
    assert all(['out'] in path.get('excluded_paths', [])
               for path in result.trace_parameter('kwargs')['return_paths'])
    assert not any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)


def test_nested_operation_failure_is_not_erased_by_the_outer_container_protocol():
    result = analyze('nested_argument_failure')
    assert any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)
    assert all(['out'] not in path.get('excluded_paths', [])
               for path in result.trace_parameter('kwargs')['return_paths'])


def test_unknown_body_exit_does_not_bind_a_confirmed_empty_exception_triple():
    result = analyze('unknown_body')
    call = next(call for call in exits(result)
                if call.implicit_protocol['incoming_exit']['kind'] == 'unknown')
    assert call.implicit_protocol['completion'] == 'unconfirmed'
    assert all(argument.get('literal') is None for argument in call.argument_sources[1:])
    assert any(boundary['reason'] == 'context_exit_unmodeled'
               and 'context_exit_incoming_unresolved' in boundary['issues'] for boundary in result.boundaries)


@pytest.mark.parametrize('budget', [1, 2, 3])
def test_call_budget_exhaustion_during_implicit_enter_or_exit_is_not_an_exception(budget):
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname='normal'), max_call_contexts=budget)
    assert any(boundary['reason'] in ('budget_exceeded', 'context_enter_budget', 'context_exit_budget')
               for boundary in result.boundaries)
