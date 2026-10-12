import copy
import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures/value_flow_with'


def analyze(entry, analyzer=None, **options):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='cases', qualname=entry), **options)


def contexts(result):
    return next(function['context_managers'] for function in result.functions
                if function['function'] == result.to_dict()['entry'])


@pytest.mark.parametrize('entry,target', [
    ('with_receiver', 'with_receiver.Session.request'),
    ('protocol_narrowing', 'SimpleSession.request')])
def test_minimal_with_binds_the_source_enter_result_and_analyzes_body(entry, target):
    result = analyze(entry, max_depth=3)
    body = result.find_calls(callee_name='session.request')[0]
    assert body.analysis_status == 'analyzed'
    assert body.target.qualname == target
    assert any(value['source'] == 'kwargs' for argument in body.argument_sources
               for value in argument['sources'] if value['kind'] == 'parameter')
    assert any(value.get('context_manager_return', {}).get('identity') == 'receiver_alias'
               for value in body.receiver_sources)
    fact = contexts(result)[0]
    assert fact['enter']['return_status'] == 'source_proven'
    assert fact['exit']['effects_status'] == 'source_noop'
    enter = next(call for call in result.calls if call.id == fact['enter']['call_id'])
    assert enter.implicit_protocol['method'] == '__enter__'
    assert enter.implicit_protocol['lookup'] == 'type_mro'
    assert enter.implicit_protocol['runtime_target_confirmed'] is False
    assert enter.target and enter.target.qualname.endswith('.__enter__')
    assert enter.receiver_sources
    assert any(item['source_text'].strip().startswith('return')
               for value in enter.result_sources for item in value.get('evidence', []))
    assert any(condition.get('context_enter') == enter.id
               and condition['completion'] == 'normal_return'
               for value in body.receiver_sources for condition in value.get('conditions', []))
    assert any(boundary['reason'] == 'dynamic_method_override_possible'
               and boundary.get('call_id') == body.id for boundary in result.boundaries)
    assert not any(boundary['reason'] == 'unsupported_statement'
                   and boundary.get('function') == result.to_dict()['entry'] for boundary in result.boundaries)


def test_enter_can_return_a_different_instance_without_reusing_the_manager_type():
    result = analyze('other_receiver')
    call = result.find_calls(callee_name='session.request')[0]
    assert call.target.qualname == 'Other.request'
    assert call.target_candidates == [result.describe_call_flow(call.id)['target']]
    assert all(value.get('instance_type', {}).get('qualname') != 'OtherManager'
               for value in call.receiver_sources)
    assert contexts(result)[0]['enter']['return_status'] == 'source_proven'
    assert any(value.get('context_manager_return', {}).get('identity') == 'return_instance'
               for value in call.receiver_sources)


@pytest.mark.parametrize('entry', ['unknown_return', 'unknown_receiver', 'unknown_enter',
    'none_return', 'mixed_return', 'decorated_enter', 'async_enter', 'generator_enter',
    'customized_lookup', 'written_enter', 'descriptor_enter', 'class_enter', 'recursive_enter'])
def test_unproven_protocol_or_return_does_not_inherit_the_manager_receiver(entry):
    result = analyze(entry)
    call = result.find_calls(callee_name='session.request')[0]
    assert call.target is None
    assert call.target_candidates == []
    assert call.target_status == 'receiver_unresolved'
    assert any(boundary['reason'].startswith('context_enter_') for boundary in result.boundaries)
    assert contexts(result)[0]['enter']['return_status'] != 'source_proven'


def test_enter_that_only_raises_does_not_analyze_the_body_as_a_normal_path():
    result = analyze('enter_raises')
    call = result.find_calls(callee_name='session.request')[0]
    assert call.analysis_status == 'not_analyzed'
    assert call.target is None and call.argument_sources == []
    assert contexts(result)[0]['enter']['completion'] == 'no_normal_return'
    assert any(boundary['reason'] == 'context_enter_no_normal_return' for boundary in result.boundaries)


def test_unknown_exit_effect_does_not_stop_source_proven_body_but_is_not_erased():
    result = analyze('unknown_exit')
    assert result.find_calls(callee_name='session.request')[0].target.qualname == 'SimpleSession.request'
    assert contexts(result)[0]['exit']['effects_status'] == 'unmodeled'
    assert any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)


def test_normal_body_preserves_existing_container_protocol_and_current_contents():
    result = analyze('normal_body')
    pop = result.find_calls(callee_name='kwargs.pop')[0]
    assert pop.target_status == 'local_container_protocol'
    assert pop.effects[0]['element_path'] == ['out']
    after = result.find_calls(callee_name='fixed')[0]
    values = [value for argument in after.argument_sources for value in argument['sources']]
    assert any(value.get('excluded_paths') == [['out']] for value in values)
    assert any(value['kind'] == 'parameter' and value['source'] == 'kwargs' for value in values)


def test_unmodeled_exit_cannot_preserve_a_strong_element_exclusion_after_with():
    result = analyze('unknown_exit_contents')
    after = result.find_calls(callee_name='fixed')[0]
    assert after.analysis_status == 'analyzed'
    assert not any(['out'] in value.get('excluded_paths', [])
                   for argument in after.argument_sources for value in argument['sources'])
    assert any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)


@pytest.mark.parametrize('entry', ['multiple', 'nested', 'second_context_uses_first'])
def test_contexts_enter_left_to_right_and_keep_distinct_return_evidence(entry):
    result = analyze(entry)
    facts = contexts(result)
    assert len(facts) == 2
    enter_ids = [fact['enter']['call_id'] for fact in facts]
    assert len(set(enter_ids)) == 2
    calls = [call for call in result.calls if call.implicit_protocol.get('method') == '__enter__']
    assert [call.id for call in calls] == enter_ids
    if entry == 'second_context_uses_first':
        assert result.find_calls(callee_name='second.request')[0].target.qualname == 'SimpleSession.request'
    else:
        assert result.find_calls(callee_name='second.request')[0].target.qualname == 'Other.request'


@pytest.mark.parametrize('entry', ['early_return', 'raise_in_body', 'body_break', 'body_continue'])
def test_body_exit_states_do_not_fall_through_the_with(entry):
    result = analyze(entry)
    call = result.find_calls(callee_name='unreachable')[0]
    assert call.analysis_status == 'not_analyzed'
    assert call.argument_sources == []


def test_no_as_still_analyzes_normal_body():
    result = analyze('no_as')
    assert result.find_calls(callee_name='fixed')[0].target.qualname == 'fixed'
    assert contexts(result)[0]['as_target'] is None


def test_async_with_remains_an_explicit_unsupported_protocol():
    result = analyze('async_with')
    assert result.find_calls(callee_name='session.request')[0].analysis_status == 'not_analyzed'
    assert any(boundary['reason'] == 'async_with_unsupported' for boundary in result.boundaries)


def test_repeated_analysis_serialization_and_expansion_do_not_share_context_facts():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyze('protocol_narrowing', analyzer)
    original = copy.deepcopy(result.to_dict())
    json.dumps(original)
    analyze('unknown_return', analyzer)
    assert analyze('protocol_narrowing', analyzer).to_dict() == original
    call = result.find_calls(callee_name='session.request')[0]
    expanded = analyzer.expand(result, call.id)
    assert result.to_dict() == original
    assert contexts(expanded) == contexts(result)


def test_import_alias_and_inherited_protocol_keep_the_actual_receiver_class():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef(module='imported', qualname='root'), max_depth=3)
    call = result.find_calls(callee_name='session.request')[0]
    assert call.target.module == 'protocols' and call.target.qualname == 'Base.request'
    assert call.receiver_sources[0]['instance_type']['qualname'] == 'Child'
    assert contexts(result)[0]['enter']['target']['qualname'] == 'Base.__enter__'
    assert any(value['source_text'].strip() == 'return self'
               and value['file_path'].endswith('protocols.py')
               for source in call.receiver_sources for value in source['evidence'])


@pytest.mark.parametrize('entry', ['required_enter', 'no_receiver_enter', 'missing_exit'])
def test_invalid_source_protocol_binding_does_not_report_a_normal_body(entry):
    result = analyze(entry)
    call = result.find_calls(callee_name='session.request')[0]
    assert call.analysis_status == 'not_analyzed'
    assert call.target is None and call.argument_sources == []
    assert any(boundary['reason'].startswith('context_') for boundary in result.boundaries)


def test_exit_with_invalid_signature_is_not_classified_as_a_source_noop():
    result = analyze('required_exit')
    assert result.find_calls(callee_name='session.request')[0].target.qualname == 'SimpleSession.request'
    assert contexts(result)[0]['exit']['effects_status'] == 'unmodeled'
    assert 'binding_unconfirmed' in contexts(result)[0]['exit']['issues']


def test_source_proven_exception_suppression_is_not_a_false_noop():
    result = analyze('suppressing_exit')
    assert contexts(result)[0]['exit']['effects_status'] == 'source_modeled'
    assert not any(boundary['reason'] == 'context_exit_unmodeled' for boundary in result.boundaries)
    assert result.find_calls(callee_name='unknown_after')[0].analysis_status == 'analyzed'


def test_unknown_exit_invalidates_receiver_type_after_the_body():
    result = analyze('unknown_exit_receiver')
    before, after = result.find_calls(callee_name='session.request')
    assert before.target.qualname == 'SimpleSession.request'
    assert after.target is None and after.target_status == 'receiver_unresolved'


def test_unknown_enter_effect_cannot_keep_a_prior_strong_exclusion():
    result = analyze('enter_effects_after_pop')
    call = result.find_calls(callee_name='fixed')[0]
    assert not any(['out'] in value.get('excluded_paths', [])
                   for argument in call.argument_sources for value in argument['sources'])
    assert any(boundary['reason'] == 'context_enter_effects_unmodeled' for boundary in result.boundaries)


def test_fresh_enter_allocations_are_instantiated_per_call_not_cached_objects():
    result = analyze('distinct_allocations')
    sources = [call.receiver_sources[0]['context_manager_return']['object_source']
               for name in ('first.request', 'second.request') for call in result.find_calls(callee_name=name)]
    assert sources[0] != sources[1]
    assert len(contexts(result)) == 2


def test_enter_proof_budget_exhaustion_keeps_an_explicit_boundary(monkeypatch):
    import pcresolve.flow as flow
    monkeypatch.setattr(flow, '_CONTEXT_PROTOCOL_NODE_LIMIT', 1, raising=False)
    result = analyze('protocol_narrowing')
    call = result.find_calls(callee_name='session.request')[0]
    assert call.target is None and call.target_status == 'receiver_unresolved'
    assert 'context_enter_budget' in contexts(result)[0]['enter']['issues']
    assert any(boundary['reason'] == 'context_enter_budget' for boundary in result.boundaries)


def test_failure_of_a_later_enter_retains_the_prior_context_cleanup_boundary():
    result = analyze('second_enter_fails')
    assert result.find_calls(callee_name='second.request')[0].analysis_status == 'not_analyzed'
    assert any(boundary['reason'] == 'context_exit_unmodeled'
               and boundary.get('item_index') == 0 for boundary in result.boundaries)


@pytest.mark.parametrize('entry', ['reclassified_manager', 'dynamic_constructor_manager',
    'bound_mutator_manager', 'alias_class_write_manager', 'helper_class_write_manager'])
def test_visible_instance_class_replacement_cannot_prove_the_original_protocol(entry):
    result = analyze(entry)
    call = result.find_calls(callee_name='session.request')[0]
    assert call.target is None and call.target_candidates == []
    assert contexts(result)[0]['enter']['return_status'] == 'unconfirmed'


def test_unused_method_dynamic_writes_are_not_enter_path_type_modifications():
    result = analyze('idle_method_manager')
    assert result.find_calls(callee_name='session.request')[0].target.qualname == 'SimpleSession.request'
    assert contexts(result)[0]['enter']['return_status'] == 'source_proven'
    assert next(call for call in result.calls if call.implicit_protocol).implicit_protocol[
        'runtime_target_confirmed'] is False
