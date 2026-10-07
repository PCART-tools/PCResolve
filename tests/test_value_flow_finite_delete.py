from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_finite_delete'


def analyze(entry, **limits):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=3, **limits)


def named(result, name, caller):
    return next(call for call in result.find_calls(callee_name=name)
                if call.caller.qualname == caller)


def roots(call):
    return [value for argument in call.argument_sources for value in argument['sources']
            if value['kind'] == 'parameter' and value['source'] == 'kwargs']


def test_finite_sequence_removals_keep_roots_conditions_binding_and_completion():
    result = analyze('root')
    call = named(result, 'remove_keys', 'root')
    effects = [effect for effect in call.effects if effect['kind'] == 'mapping_element']
    assert {tuple(effect['element_path']) for effect in effects} == {('out',), ('p',)}
    for effect in effects:
        assert effect['completion'] == 'normal_return'
        assert effect['may_raise'] is None
        assert any(root['name'] == 'kwargs' for root in effect['mapping'])
        assert effect['sequence_binding']['parameter'] == 'keys'
        assert effect['sequence_binding']['literal']['value'] == ['out', 'p']
        assert effect['operation_conditions'][0]['test']['source_text'] == 'key in mapping'
        assert effect['loop_evidence']['source_text'].startswith('for key in keys:')
        assert effect['evidence'] and effect['call_evidence']
    assert all(['out'] in value['excluded_paths'] and ['p'] in value['excluded_paths']
               for value in roots(named(result, 'sink', 'root')))


def test_finite_sequence_effects_then_return_alias_observe_current_contents():
    result = analyze('returned')
    assert named(result, 'clean', 'returned').result_sources[0]['container_object']
    assert named(result, 'forwarded.pop', 'returned').target_status == 'local_container_protocol'
    for call in result.find_calls(callee_name='sink'):
        assert roots(call)
        assert all(['out'] in value['excluded_paths'] and ['p'] in value['excluded_paths']
                   and ['unused'] in value['excluded_paths'] for value in roots(call))


def test_finite_mapping_and_independent_sequences_do_not_share_state():
    result = analyze('finite')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']
    result = analyze('independent')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


@pytest.mark.parametrize('entry', ['unknown_keys', 'unknown_mapping', 'non_string',
                                  'unknown_call', 'exception_path', 'mutated_keys',
                                  'recursive_entry'])
def test_unclosed_sequence_or_behavior_does_not_apply_finite_strong_update(entry):
    result = analyze(entry)
    assert not any(effect.get('state_after') == 'absent' for call in result.calls
                   if call.caller.qualname == entry for effect in call.effects)
    assert any(boundary['reason'] == 'mapping_effect_unproven' for boundary in result.boundaries)


def test_caller_condition_does_not_prove_unconditional_final_absence():
    result = analyze('conditional')
    call = named(result, 'remove_keys', 'conditional')
    assert call.effects[0]['state_after'] == 'conditional' and call.effects[0]['conditions']
    assert any(not value.get('excluded_paths')
               for value in roots(named(result, 'sink', 'conditional')))


def test_clear_followed_by_finite_delete_never_restores_content():
    result = analyze('cleared')
    assert not roots(named(result, 'sink', 'cleared'))


def test_later_unknown_ordinary_mapping_escape_widens_previous_removals():
    result = analyze('after_unknown')
    assert roots(named(result, 'sink', 'after_unknown'))
    assert all(not value.get('excluded_paths')
               for value in roots(named(result, 'sink', 'after_unknown')))


def test_finite_sequence_proof_has_budget_boundaries():
    result = analyze('root', max_functions=1, max_call_contexts=1)
    assert any('budget' in boundary['reason'] for boundary in result.boundaries)


def test_warning_name_does_not_prove_completion_but_deletion_site_is_reported():
    result = analyze('unknown_call')
    call = named(result, 'warning', 'unknown_call')
    site = next(effect for effect in call.effects if effect['kind'] == 'mapping_element')
    assert site['element_path'] == ['out']
    assert site['completion'] == 'unproven' and site['state_after'] == 'unknown'
    assert site['reachability'] == 'not_proven'
    assert site['operation_conditions'] and site['sequence_binding']
    assert all(not value.get('excluded_paths')
               for value in roots(named(result, 'sink', 'unknown_call')))


@pytest.mark.parametrize('entry', ['helper_mutated_keys', 'helper_mutated_key_alias'])
def test_helper_sequence_mutation_cannot_delete_using_stale_incoming_keys(entry):
    result = analyze(entry)
    assert not any(effect.get('state_after') == 'absent' for call in result.calls
                   if call.caller.qualname == entry for effect in call.effects)
    assert any(boundary['reason'] == 'mapping_effect_unproven'
               for boundary in result.boundaries)
    assert all(not value.get('excluded_paths') for call in result.find_calls(callee_name='sink')
               for value in roots(call))
