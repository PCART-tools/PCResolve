from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_callable_context'


def analyze(entry, **limits):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=4, **limits)


def inner(result, caller='invoke'):
    return next(call for call in result.calls
                if call.caller.qualname == caller and call.callee_name == 'metric')


@pytest.mark.parametrize('entry', ['root', 'aliased', 'module_alias'])
def test_callable_actual_reaches_helper_and_multihop_alias(entry):
    call = inner(analyze(entry))
    assert call.target.module == 'helpers' and call.target.qualname == 'fixed'
    assert call.target_status == 'incoming_callable'
    assert call.callable_sources[0]['callable_type']['qualname'] == 'fixed'
    assert call.callable_sources[0]['callable_evidence']
    assert call.analysis_contexts[0]['incoming_call_id']


def test_expand_consumes_existing_binding_without_modifying_snapshot():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef(module='cases', qualname='root'))
    call = result.find_calls(callee_name='invoke')[0]
    expanded = analyzer.expand(result, call.id)
    assert inner(expanded).target.qualname == 'fixed'
    assert not result.find_calls(callee_name='metric')


def test_distinct_callback_contexts_are_not_cached_or_reported_as_one_target():
    call = inner(analyze('contexts'))
    assert call.target is None
    assert {item['qualname'] for item in call.target_candidates} == {'fixed', 'accepts'}
    assert {item['target']['qualname'] for item in call.analysis_contexts} == {'fixed', 'accepts'}
    assert len({item['incoming_call_id'] for item in call.analysis_contexts}) == 2
    mixed = inner(analyze('mixed'))
    assert mixed.target is None and mixed.target_status == 'definition_unavailable'
    assert any(item['target'] is None for item in mixed.analysis_contexts)


def test_generic_helper_and_unknown_or_string_actual_do_not_inherit_callback_identity():
    generic = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='helpers', qualname='invoke'))
    assert inner(generic).target is None
    for entry in ('unknown', 'named'):
        assert inner(analyze(entry)).target is None


def test_parameter_rebinding_and_attribute_write_override_incoming_identity():
    assert inner(analyze('rebound'), 'replace').target.qualname == 'accepts'
    branch = inner(analyze('branch'), 'conditional')
    assert branch.target is None
    assert {item['qualname'] for item in branch.target_candidates} == {'fixed', 'accepts'}
    assert inner(analyze('modified'), 'overwrite').target is None


@pytest.mark.parametrize('entry', ['literal_dispatch', 'local_dispatch'])
def test_closed_literal_dispatch_resolves_by_key_provenance(entry):
    call = next(call for call in analyze(entry).calls if call.caller.qualname == entry)
    assert call.target.qualname == 'fixed'
    assert call.callable_sources and call.target_status == 'literal_dispatch'


def test_dynamic_dispatch_has_only_source_bounded_alternatives():
    call = next(call for call in analyze('variable_dispatch').calls
                if call.caller.qualname == 'variable_dispatch')
    assert call.target is None and call.target_status == 'bounded_alternatives'
    assert {item['qualname'] for item in call.target_candidates} == {'fixed', 'accepts'}


@pytest.mark.parametrize('entry', ['dirty_dispatch', 'escaped_dispatch', 'incomplete_dispatch'])
def test_unknown_table_modification_or_incomplete_source_keeps_boundary(entry):
    result = analyze(entry)
    call = next(call for call in result.calls if call.caller.qualname == entry)
    assert call.target is None
    assert any(boundary.get('call_id') == call.id for boundary in result.boundaries)


def test_context_budget_still_bounds_callable_expansion():
    result = analyze('contexts', max_functions=1)
    assert any(boundary['reason'] == 'budget_exceeded' for boundary in result.boundaries)


def test_unknown_escape_does_not_leave_a_unique_callable_proof():
    result = analyze('escaped_local')
    call = result.find_calls(callee_name="table['fixed']")[0]
    assert call.target is None
    assert inner(analyze('callback_escape')).target is None


def test_mixed_actual_retains_candidate_but_explicitly_leaves_source_range_open():
    result = analyze('mixed_actual')
    call = inner(result)
    assert call.target is None
    assert call.target_status == 'definition_unavailable'
    assert {value['qualname'] for value in call.target_candidates} == {'fixed'}
    assert any(boundary['reason'] == 'callable_identity_incomplete' for boundary in result.boundaries)


def test_callable_object_write_through_dispatch_slot_invalidates_target():
    result = analyze('modified_table_value')
    call = result.find_calls(callee_name="table['fixed']")[0]
    assert call.target is None


def test_conditional_parameter_deletion_keeps_open_binding_boundary():
    call = next(call for call in analyze('removed_root').find_calls(callee_name='callback')
                if call.caller.qualname == 'removed_callback')
    assert call.target is None and call.target_status == 'definition_unavailable'


def test_expand_merged_edge_does_not_select_last_incoming_callback():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef(module='cases', qualname='relay_contexts'), max_depth=2)
    call = result.find_calls(callee_name='invoke')[0]
    expanded = analyzer.expand(result, call.id)
    assert inner(expanded).target is None
    assert {value['qualname'] for value in inner(expanded).target_candidates} == {'fixed', 'accepts'}


def test_module_literal_table_does_not_use_callers_local_binding():
    call = analyze('module_table_shadow').find_calls(callee_name="TARGETS['fixed']")[0]
    assert call.target.module == 'helpers' and call.target.qualname == 'fixed'
