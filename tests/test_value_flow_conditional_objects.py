from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_conditional_objects'


def analyze(entry, **limits):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=3, **limits)


def named(result, name, caller):
    return next(call for call in result.find_calls(callee_name=name)
                if call.caller.qualname == caller)


def roots(call):
    return [value for argument in call.argument_sources for value in argument['sources']
            if value['kind'] == 'parameter' and value['source'] == 'kwargs']


def test_known_early_return_retains_shape_alias_and_condition_evidence():
    result = analyze('root')
    call = named(result, 'helper', 'root')
    obj = call.result_sources[0]['container_object']
    assert obj['identity'] == 'argument_alias' and obj['container_shape'] == 'dict'
    assert obj['conditions'][0]['test']['source_text'] == 'not values'
    assert obj['conditions'][0]['branch'] is True
    assert obj['conditions'][0]['binding']['literal']['type'] == 'tuple'
    assert named(result, 'mapping.pop', 'root').target_status == 'local_container_protocol'
    assert all(['out'] in value['excluded_paths']
               for value in roots(named(result, 'fixed', 'root')))
    assert not any(call.caller.qualname == 'helper'
                   and call.callee_name == 'unknown_effect' and call.analysis_status == 'analyzed'
                   for call in result.calls)


def test_early_alias_clear_and_modeled_mutation_use_current_shared_contents():
    result = analyze('alias_clear')
    assert not roots(named(result, 'fixed', 'alias_clear'))
    result = analyze('mutated')
    for call in result.find_calls(callee_name='fixed'):
        assert roots(call)
        assert all(['before'] in value['excluded_paths'] and ['out'] in value['excluded_paths']
                   for value in roots(call))


def test_finite_input_does_not_regain_open_content():
    result = analyze('finite')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']
    assert named(result, 'mapping.pop', 'finite').target_status == 'local_container_protocol'


@pytest.mark.parametrize('entry', ['unsafe', 'unknown'])
def test_other_or_unknown_path_does_not_claim_unconditional_identity(entry):
    result = analyze(entry)
    call = named(result, 'helper', entry)
    assert not any(value.get('container_object') and not value.get('value_incomplete')
                   for value in call.result_sources)
    assert named(result, 'mapping.pop', entry).target_status == 'receiver_unresolved'
    assert any(boundary['reason'] == 'container_return_unproven' for boundary in result.boundaries)
    if entry == 'unknown':
        assert call.conditional_returns[0]['conditions'][0]['branch'] is True
        assert call.conditional_returns[0]['container_shape'] == 'dict'
        assert call.conditional_returns[0]['object_source'].endswith(':kwargs')
        assert call.conditional_returns[0]['binding']['parameter'] == 'mapping'


def test_generic_summary_retains_guarded_alias_without_claiming_global_purity():
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname='helper'))
    proofs = result.functions[0]['return_objects']
    assert proofs[0]['parameter'] == 'mapping' and proofs[0]['conditions']
    assert proofs[0]['completeness'] == 'partial_paths'
    assert any(boundary['reason'] == 'definition_unavailable' for boundary in result.boundaries)


def test_known_and_unknown_contexts_do_not_share_return_object_cache():
    result = analyze('contexts')
    calls = [call for call in result.find_calls(callee_name='helper')
             if call.caller.qualname == 'contexts']
    assert calls[0].result_sources[0]['container_object']
    assert not any(value.get('container_object') for value in calls[1].result_sources)
    assert named(result, 'second.clear', 'contexts').target_status == 'receiver_unresolved'


def test_copy_return_cannot_clear_original():
    assert roots(named(analyze('copy_clear'), 'fixed', 'copy_clear'))


@pytest.mark.parametrize('entry', ['negative_mixed', 'negative_finally', 'negative_mutation',
                                  'negative_rebuilt', 'negative_escape', 'negative_recursive'])
def test_unmodeled_paths_do_not_prove_return_object(entry):
    result = analyze(entry)
    calls = [call for call in result.calls if call.callee_name.endswith('.clear')]
    assert calls and all(call.target_status == 'receiver_unresolved' for call in calls)


def test_early_return_proof_remains_budgeted():
    result = analyze('root', max_functions=1, max_call_contexts=1)
    assert any('budget' in boundary['reason'] for boundary in result.boundaries)


def test_mutated_literal_sequence_cannot_select_old_empty_branch():
    result = analyze('changed_sequence')
    call = result.find_calls(callee_name='helper')[0]
    assert not any(value.get('container_object') for value in call.result_sources)


def test_unknown_guard_call_does_not_claim_unchanged_content_on_early_path():
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname='effectful_guard'))
    assert not result.functions[0].get('return_objects')


def test_literal_branch_limit_retains_boundary_and_no_strong_alias_update():
    result = analyze('budget_branch')
    assert any(boundary['reason'] == 'literal_branch_budget' for boundary in result.boundaries)
    call = result.find_calls(callee_name='deep_branch')[0]
    assert not any(value.get('container_object') for value in call.result_sources)
