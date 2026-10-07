from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_class_state'


def analyze(entry, **limits):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=4, **limits)


def method(result, caller):
    return next(call for call in result.calls if call.caller.qualname == caller
                and call.callee_name.endswith('.initialize'))


def test_mutable_configuration_retains_guarded_source_candidate_not_runtime_default():
    result = analyze('root')
    call = method(result, 'Configurable.allocate')
    assert call.target is None and call.target_status == 'receiver_unresolved'
    assert {value['qualname'] for value in call.target_candidates} == {'Backend.initialize'}
    assert call.receiver_sources[0]['instance_candidates'][0]['qualname'] == 'Backend'
    assert any(boundary['reason'] == 'class_attribute_state_unknown' for boundary in result.boundaries)
    configured = result.find_calls(callee_name='cls.configured')[0]
    value = next(value for value in configured.result_sources if value.get('class_type'))
    assert value['value_incomplete'] and value['conditions']
    evidence = value['attribute_provenance'][0]
    assert evidence['attribute'] == 'implementation'
    assert evidence['assignment']['source_text'] == 'cls.implementation = cls.default()'
    assert evidence['read']['source_text'] == 'cls.implementation'


def test_derived_receiver_context_keeps_its_own_default_candidate():
    first = analyze('root')
    second = analyze('derived')
    assert {value['qualname'] for value in method(first, 'Configurable.allocate').target_candidates} == {'Backend.initialize'}
    assert {value['qualname'] for value in method(second, 'Configurable.allocate').target_candidates} == {'Other.initialize'}


def test_same_receiver_definite_write_read_supports_allocation_source_target():
    call = method(analyze('Configurable.direct_write'), 'Configurable.direct_write')
    assert call.target.qualname == 'Backend.initialize'
    assert call.receiver_sources[0]['instance_type']['qualname'] == 'Backend'
    assert call.receiver_sources[0]['attribute_provenance']


def test_closed_mixed_attribute_states_produce_bounded_candidates():
    call = method(analyze('Configurable.mixed'), 'Configurable.mixed')
    assert call.target is None and call.target_status == 'bounded_alternatives'
    assert {value['qualname'] for value in call.target_candidates} == {'Backend.initialize', 'Other.initialize'}


def test_literal_selected_branch_has_condition_and_source_identity():
    call = method(analyze('known'), 'known')
    assert call.target.qualname == 'Backend.initialize'
    assert call.receiver_sources[0]['conditions']


@pytest.mark.parametrize('entry,caller', [
    ('Configurable.overwrite', 'Configurable.overwrite'),
    ('Configurable.escape', 'Configurable.escape'),
    ('generic', 'generic'), ('rebound', 'rebound'), ('CustomState.root', 'CustomState.root')])
def test_unknown_write_receiver_allocator_or_custom_construction_keeps_boundary(entry, caller):
    result = analyze(entry)
    call = method(result, caller)
    assert call.target is None and not call.target_candidates
    assert any(boundary.get('call_id') == call.id for boundary in result.boundaries)


def test_configuration_proof_respects_recursion_and_budget():
    result = analyze('root', max_functions=1, max_call_contexts=1)
    assert any('budget' in boundary['reason'] for boundary in result.boundaries)


def test_conditional_class_value_also_supports_source_constructor_result_candidate():
    call = method(analyze('Configurable.constructor'), 'Configurable.constructor')
    assert call.target is None and call.target_status == 'receiver_unresolved'
    assert {value['qualname'] for value in call.target_candidates} == {'Backend.initialize'}


def test_method_monkeypatch_does_not_become_a_data_attribute_proof():
    result = analyze('Configurable.patched')
    call = result.find_calls(callee_name='cls.default')[0]
    assert call.target is None
