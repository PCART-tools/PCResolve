## @package tests.test_value_flow_container_copies

import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_container_copies'


def analyze(entry, analyzer=None, **limits):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=2, **limits)


def named(result, name):
    return result.find_calls(callee_name=name)[0]


def roots(call, name):
    return [value for argument in call.argument_sources for value in argument['sources']
            if value['kind'] == 'parameter' and value['source'] == name]


def returned_object(call):
    return next(value['container_object'] for value in call.result_sources
                if value.get('container_object'))


@pytest.mark.parametrize('entry,callee', [('copy_open', 'kwargs.copy'), ('dict_open', 'dict')])
def test_dict_copy_preserves_open_elements_but_has_a_fresh_identity(entry, callee):
    result = analyze(entry)
    call = named(result, callee)
    obj = returned_object(call)
    assert obj['container_shape'] == 'dict'
    assert obj['identity'] == 'shallow_copy'
    assert obj['source'] != obj['copied_from']
    assert call.target is None and call.target_candidates == []
    assert call.target_status == 'local_container_protocol'
    assert call.binding_status == 'complete'
    assert named(result, 'copied.pop').target_status == 'local_container_protocol'
    sources = roots(named(result, 'sink'), 'kwargs')
    assert sources and all(value['output_path'] == ['*'] for value in sources)
    assert all(['out'] in value.get('excluded_paths', []) for value in sources)
    assert any(item['operation'] == 'copy' and item['output_container'] == obj['source']
               for item in call.effects)
    assert any(span['source_text'] == callee + '(kwargs)' if callee == 'dict'
               else span['source_text'] == 'kwargs.copy()'
               for value in call.result_sources for span in value['evidence'])
    json.dumps(result.to_dict())


@pytest.mark.parametrize('entry', ['clear_copy', 'clear_original'])
def test_copy_mutations_do_not_share_top_level_identity(entry):
    result = analyze(entry)
    first, last = [call for call in result.find_calls(callee_name='sink')
                   if call.caller.qualname == entry]
    assert not roots(first, 'kwargs')
    assert roots(last, 'kwargs')


@pytest.mark.parametrize('entry', ['copy_cleared', 'dict_cleared', 'list_cleared'])
def test_copy_reads_current_cleared_contents_and_never_restores_old_dependencies(entry):
    result = analyze(entry)
    parameter = 'value' if entry == 'list_cleared' else 'kwargs'
    assert not roots(named(result, 'sink'), parameter)
    assert not result.trace_parameter(parameter)['return_paths']


def test_finite_copy_does_not_turn_into_an_open_mapping():
    result = analyze('finite_copy')
    sources = roots(named(result, 'sink'), 'value')
    assert sources and all(value['output_path'] == ['allowed'] for value in sources)
    assert returned_object(named(result, 'original.copy'))['identity'] == 'shallow_copy'


def test_copy_carries_current_exclusions():
    result = analyze('excluded_copy')
    assert all(['out'] in source.get('excluded_paths', [])
               for source in roots(named(result, 'sink'), 'kwargs'))


def test_shallow_copy_keeps_nested_object_aliases():
    result = analyze('shallow_copy')
    assert named(result, "copied['payload'].clear").target_status == 'local_container_protocol'
    assert not roots(named(result, 'sink'), 'value')
    assert not result.trace_parameter('value')['return_paths']


def test_two_allocations_and_repeated_queries_do_not_share_contents():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyze('repeated_copies', analyzer)
    saved = first.to_dict()
    assert not roots(named(first, 'sink'), 'x')
    assert roots(named(first, 'sink'), 'y')
    analyze('clear_copy', analyzer)
    assert analyze('repeated_copies', analyzer).to_dict() == saved


@pytest.mark.parametrize('entry,callee,shape', [('list_args', 'list', 'list'),
    ('tuple_list', 'tuple', 'tuple'), ('list_finite', 'list', 'list'),
    ('tuple_args', 'tuple', 'tuple')])
def test_sequence_conversion_retains_elements_and_usable_container_shape(entry, callee, shape):
    result = analyze(entry)
    obj = returned_object(named(result, callee))
    assert obj['container_shape'] == shape
    assert named(result, callee).target is None
    if entry == 'list_finite':
        assert not result.trace_parameter('x')['return_paths']
        assert result.trace_parameter('y')['return_paths']
    elif entry == 'tuple_list':
        assert roots(named(result, 'sink'), 'value')
    else:
        assert result.trace_parameter('args')['return_paths']


@pytest.mark.parametrize('entry,state,insertion', [
    ('setdefault_present', 'present', 'never'), ('setdefault_missing', 'absent', 'always'),
    ('setdefault_unknown', 'unknown', 'conditional'), ('setdefault_excluded', 'absent', 'always'),
    ('setdefault_after_clear', 'absent', 'always'), ('setdefault_existing_none', 'present', 'never')])
def test_setdefault_distinguishes_existing_missing_and_unknown_keys(entry, state, insertion):
    result = analyze(entry)
    call = named(result, 'mapping.setdefault' if entry in (
        'setdefault_present', 'setdefault_missing', 'setdefault_existing_none') else 'kwargs.setdefault')
    assert call.target is None and call.target_candidates == []
    assert call.target_status == 'local_container_protocol'
    assert call.binding_status == 'complete'
    effect = next(item for item in call.effects if item['operation'] == 'setdefault')
    assert effect['state_before'] == state and effect['insertion'] == insertion
    assert effect['element_path'] == ['out']
    assert effect['completion'] == 'normal_return'
    paths = result.trace_parameter('default')['return_paths']
    assert bool(paths) == (insertion != 'never')
    if entry == 'setdefault_present':
        assert result.trace_parameter('existing')['return_paths']
    if entry == 'setdefault_unknown':
        assert any(value.get('projection') == ['out']
                   for value in result.trace_parameter('kwargs')['return_paths'])
        assert any(value.get('conditions') for value in paths)
    if entry == 'setdefault_after_clear':
        assert not roots(named(result, 'sink'), 'kwargs')


def test_default_none_adds_no_old_or_fabricated_parameter_dependency():
    result = analyze('setdefault_none')
    call = named(result, 'mapping.setdefault')
    assert call.target_status == 'local_container_protocol'
    assert not call.mutation_flows
    assert all(value['output_path'] == ['allowed'] for value in roots(named(result, 'sink'), 'value'))


def test_setdefault_alias_and_nested_default_have_correct_object_semantics():
    result = analyze('setdefault_alias')
    assert roots(named(result, 'sink'), 'kwargs')
    default = roots(named(result, 'sink'), 'default')
    assert default and all(value['output_path'] == ['out'] for value in default)
    nested = analyze('setdefault_nested')
    assert named(nested, 'payload.clear').target_status == 'local_container_protocol'
    assert not nested.trace_parameter('value')['return_paths']


def test_repeated_setdefault_does_not_override_an_existing_value():
    result = analyze('setdefault_twice')
    assert not result.trace_parameter('second')['return_paths']
    assert result.trace_parameter('first')['return_paths']
    assert result.trace_parameter('kwargs')['return_paths']


def test_default_expression_is_evaluated_before_key_presence():
    result = analyze('default_eager')
    effect = next(item for item in named(result, 'mapping.setdefault').effects
                  if item['operation'] == 'setdefault')
    assert effect['state_before'] == 'absent'
    assert not roots(named(result, 'sink'), 'value')


@pytest.mark.parametrize('entry', ['mixed_copy', 'unknown_copy', 'unknown_dict',
    'projected_copy', 'shadowed_dict', 'shadowed_list', 'local_shadow', 'custom_copy'])
def test_unknown_or_custom_receiver_never_acquires_builtin_copy_identity(entry):
    result = analyze(entry)
    call = named(result, 'copied.clear')
    assert call.target_status == 'receiver_unresolved'
    assert not call.effects and not any(value.get('container_object') for value in call.receiver_sources)
    assert result.boundaries


@pytest.mark.parametrize('entry,callee', [('custom_default', 'original.setdefault'),
    ('invalid_copy', 'kwargs.copy'), ('invalid_default', 'kwargs.setdefault')])
def test_custom_or_invalid_protocol_is_not_a_builtin_effect(entry, callee):
    result = analyze(entry)
    call = named(result, callee)
    assert call.target_status != 'local_container_protocol'
    assert not call.effects


def test_unknown_key_and_escaped_contents_retain_uncertainty():
    dynamic = analyze('setdefault_dynamic')
    assert any(item.get('call_id') == named(dynamic, 'kwargs.setdefault').id
               and item['reason'] == 'container_effect_unknown' for item in dynamic.boundaries)
    escaped = analyze('copy_escape')
    assert any(item['reason'] == 'container_copy_unproven' for item in escaped.boundaries)
    assert any(item.get('callee_name') == 'external' or item['reason'] == 'definition_unavailable'
               for item in escaped.boundaries)


def test_copy_after_conditional_clear_keeps_only_a_conditional_open_source():
    result = analyze('conditional_copy')
    assert roots(named(result, 'sink'), 'kwargs')
    assert result.boundaries


def test_copy_obeys_call_budget_without_manufacturing_object_facts():
    result = analyze('copy_open', max_call_contexts=1)
    assert any(item['reason'] == 'budget_exceeded' for item in result.boundaries)
    assert not any(call.callee_name == 'sink' for call in result.calls
                   if call.analysis_status == 'analyzed')


def test_tuple_of_proven_tuple_reuses_identity_without_a_false_fresh_allocation():
    result = analyze('tuple_identity')
    obj = returned_object(named(result, 'tuple'))
    assert obj['identity'] == 'argument_alias'
    assert obj['source'] == obj['copied_from']


def test_conditional_presence_does_not_suppress_missing_key_default():
    result = analyze('conditional_key')
    assert result.trace_parameter('existing')['return_paths']
    assert result.trace_parameter('default')['return_paths']
    effect = next(item for item in named(result, 'mapping.setdefault').effects
                  if item['operation'] == 'setdefault')
    assert effect['state_before'] == 'unknown'


def test_unknown_existing_element_does_not_acquire_the_defaults_container_type():
    result = analyze('unknown_default_container')
    assert named(result, 'payload.clear').target_status == 'receiver_unresolved'
    assert not named(result, 'payload.clear').effects


def test_escaped_finite_mapping_does_not_keep_a_definite_present_key():
    result = analyze('escaped_finite')
    assert result.trace_parameter('default')['return_paths']
    assert any(item['reason'] == 'definition_unavailable' for item in result.boundaries)


def test_copy_from_proven_returned_alias_uses_current_contents():
    result = analyze('returned_alias_copy')
    assert roots(named(result, 'sink'), 'kwargs')
    obj = returned_object(named(result, 'original.copy'))
    assert obj['source'] != returned_object(named(result, 'identity'))['source']


@pytest.mark.parametrize('entry,callee', [('copied_sequence_nested', 'copied[0].clear'),
                                        ('default_existing_container', 'payload.clear')])
def test_nested_shared_objects_retain_effects_without_reviving_content(entry, callee):
    result = analyze(entry)
    assert named(result, callee).target_status == 'local_container_protocol'
    assert not result.trace_parameter('value')['return_paths']


def test_copy_does_not_make_conditional_get_presence_definite():
    result = analyze('copied_get_default')
    assert result.trace_parameter('default')['return_paths']
