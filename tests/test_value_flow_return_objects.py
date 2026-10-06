## @package tests.test_value_flow_return_objects

import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_return_objects'


def analyze(entry, analyzer=None, **limits):
    analyzer = analyzer or FlowAnalyzer(project_root=ROOT)
    return analyzer.analyze(FunctionRef(module='cases', qualname=entry),
                            max_depth=limits.pop('max_depth', 3), **limits)


def named(result, name, caller=None):
    return next(call for call in result.find_calls(callee_name=name)
                if caller is None or call.caller.qualname == caller)


def sources(call, name):
    return [source for argument in call.argument_sources
            for source in argument['sources']
            if source['kind'] == 'parameter' and source['source'] == name]


def object_source(call):
    return next(source for source in call.result_sources
                if source.get('container_object'))


def test_identity_pop_preserves_endpoint_object_and_open_remainder():
    result = analyze('root')
    helper = named(result, 'identity', 'root')
    returned = object_source(helper)
    assert returned['kind'] == 'call_result' and returned['source'] == helper.id
    assert returned['container_object']['container_shape'] == 'dict'
    assert returned['container_object']['identity'] == 'argument_alias'
    assert returned['container_object']['parameter'] == 'mapping'
    evidence = {item.get('source_text') for item in returned['evidence']}
    assert 'return mapping' in evidence and 'identity(kwargs)' in evidence
    pop = named(result, 'mapping.pop', 'root')
    assert pop.target is None and pop.target_candidates == []
    assert pop.target_status == 'local_container_protocol'
    effect = next(item for item in pop.effects if item['kind'] == 'mapping_element')
    assert effect['element_path'] == ['out']
    assert effect['state_after'] == 'absent'
    assert any(root['name'] == 'kwargs' for root in effect['mapping'])
    remaining = sources(named(result, 'fixed', 'root'), 'kwargs')
    assert remaining and all(item['output_path'] == ['*'] for item in remaining)
    assert all(['out'] in item.get('excluded_paths', []) for item in remaining)
    assert not any(boundary.get('call_id') == pop.id
                   and boundary['reason'] == 'receiver_unresolved'
                   for boundary in result.boundaries)
    json.dumps(result.to_dict())


def test_alias_clear_updates_the_original_object():
    result = analyze('alias_clear')
    returned = object_source(named(result, 'alias_identity', 'alias_clear'))
    assert any(item['source_text'] == 'alias = mapping'
               for item in returned['evidence'])
    assert named(result, 'mapping.clear').target_status == 'local_container_protocol'
    assert not sources(named(result, 'sink', 'alias_clear'), 'kwargs')


def test_cached_symbolic_summary_does_not_share_actual_ids_between_calls():
    result = analyze('two_inputs')
    helpers = [call for call in result.find_calls(callee_name='identity')
               if call.caller.qualname == 'two_inputs']
    identities = [object_source(call)['container_object']['source'] for call in helpers]
    assert len(set(identities)) == 2
    final = named(result, 'sink', 'two_inputs')
    assert not sources(final, 'x') and sources(final, 'y')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_update_alias_mutates_original_without_losing_roots():
    result = analyze('update_alias')
    update = named(result, 'mapping.update')
    assert update.target_status == 'local_container_protocol'
    final = named(result, 'sink', 'update_alias')
    assert sources(final, 'kwargs')
    assert any(source.get('output_path') == ['added'] for source in sources(final, 'value'))


def test_list_identity_pop_updates_original_slots():
    result = analyze('list_alias')
    assert named(result, 'returned.pop').target_status == 'local_container_protocol'
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_tuple_shape_preserves_a_proven_input_object_and_projection():
    result = analyze('tuple_alias')
    assert object_source(named(result, 'identity'))['container_object']['container_shape'] == 'tuple'
    assert result.trace_parameter('x')['return_paths']


def test_local_multiple_identity_calls_preserve_shared_object():
    result = analyze('repeat_identity')
    first = object_source(named(result, 'identity'))['container_object']['source']
    second = object_source(named(result, 'alias_identity'))['container_object']['source']
    assert first == second
    assert named(result, 'second.pop').target_status == 'local_container_protocol'
    assert all(['out'] in item.get('excluded_paths', [])
               for item in sources(named(result, 'sink', 'repeat_identity'), 'kwargs'))


def test_finite_input_stays_finite_after_identity_return():
    result = analyze('finite_input')
    assert named(result, 'returned.pop').target_status == 'local_container_protocol'
    final = sources(named(result, 'sink', 'finite_input'), 'value')
    assert final and all(source.get('output_path') == ['allowed'] for source in final)


@pytest.mark.parametrize('entry,method', [
    ('negative_recapture', 'returned.clear'),
    ('negative_copy', 'returned.clear'),
    ('negative_rebuild', 'returned.pop'),
    ('negative_payload', 'returned.clear'),
    ('negative_arithmetic', 'returned.clear'),
    ('negative_boolean', 'returned.clear'),
    ('negative_mixed', 'returned.clear'),
    ('negative_implicit', 'returned.clear'),
    ('negative_mutate', 'returned.pop'),
    ('negative_escape', 'returned.clear'),
    ('negative_finalized', 'returned.clear'),
    ('negative_recursive', 'returned.clear'),
    ('negative_generator', 'returned.clear'),
    ('negative_generator_from', 'returned.clear'),
    ('modified_callable', 'returned.clear'),
    ('modified_callable_alias', 'returned.clear'),
    ('modified_nested_callable', 'returned.clear'),
])
def test_unproven_return_is_not_an_original_container_alias(entry, method):
    result = analyze(entry)
    call = named(result, method, entry)
    assert call.target_status == 'receiver_unresolved'
    assert not call.effects
    assert sources(named(result, 'sink', entry), 'kwargs')
    assert any(boundary['reason'] == 'container_return_unproven'
               for boundary in result.boundaries)


@pytest.mark.parametrize('entry', ['unknown_input', 'uncertain_binding'])
def test_unknown_shape_or_binding_does_not_acquire_object_identity(entry):
    result = analyze(entry)
    helper = named(result, 'identity', entry)
    assert not any(source.get('container_object') for source in helper.result_sources)
    assert named(result, 'returned.pop').target_status == 'receiver_unresolved'


def test_projection_derived_and_partial_values_cannot_reuse_whole_object():
    result = analyze('transformed_alias')
    for name in ('selected.clear', 'compared.clear', 'partial.clear'):
        assert named(result, name).target_status == 'receiver_unresolved'
    assert sources(named(result, 'sink', 'transformed_alias'), 'kwargs')


def test_repeat_analysis_and_expansion_do_not_cache_actual_container_ids():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyze('root', analyzer, max_depth=1)
    snapshot = first.to_dict()
    analyze('two_inputs', analyzer)
    repeated = analyze('root', analyzer, max_depth=1)
    assert first.to_dict() == snapshot
    assert object_source(named(first, 'identity')) == object_source(named(repeated, 'identity'))
    expanded = analyzer.expand(first, named(first, 'identity').id, additional_depth=1)
    assert first.to_dict() == snapshot
    assert named(expanded, 'mapping.pop').target_status == 'local_container_protocol'


def test_object_proof_obeys_budget():
    result = analyze('root', max_functions=1)
    assert any(boundary['reason'] in ('container_return_budget', 'budget_exceeded')
               for boundary in result.boundaries)


def test_direct_container_protocols_are_unchanged():
    assert named(analyze('direct_pop'), 'kwargs.pop').target_status == 'local_container_protocol'
    cleared = analyze('direct_clear')
    assert not sources(named(cleared, 'sink', 'direct_clear'), 'kwargs')


def test_cleared_return_keeps_object_endpoint_but_not_stale_element_dependencies():
    result = analyze('return_cleared')
    summary = result.functions[0]
    assert any(value['kind'] == 'call_result' and value.get('container_object')
               for value in summary['returns'])
    assert not result.trace_parameter('kwargs')['return_paths']


def test_popped_return_element_dependencies_keep_the_removed_key_exclusion():
    result = analyze('return_popped')
    paths = result.trace_parameter('kwargs')['return_paths']
    assert paths
    assert all(['out'] in path.get('excluded_paths', []) for path in paths)


def test_mapping_membership_and_delete_consume_return_object_facts():
    membership = analyze('returned_membership')
    assert any(effect['operation'] == 'membership'
               and effect['element_path'] == ['out']
               for effect in membership.functions[0]['mapping_effects'])
    deleted = analyze('returned_delete')
    assert any(effect['operation'] == 'delete'
               and effect['element_path'] == ['out']
               for effect in deleted.functions[0]['mapping_effects'])
    assert all(['out'] in source.get('excluded_paths', [])
               for source in sources(named(deleted, 'sink', 'returned_delete'), 'kwargs'))


def test_mapping_merge_creates_a_fresh_object_without_clearing_the_original():
    result = analyze('merge_returned')
    assert named(result, 'copy.clear').target_status == 'local_container_protocol'
    assert sources(named(result, 'sink', 'merge_returned'), 'value')


def test_existing_helper_clear_effect_can_consume_returned_object_reference():
    result = analyze('existing_clear_effect')
    clear = named(result, 'clear_only', 'existing_clear_effect')
    assert any(effect['kind'] == 'container_clear' for effect in clear.effects)
    assert not sources(named(result, 'sink', 'existing_clear_effect'), 'kwargs')


def test_return_object_statement_budget_retains_an_explicit_boundary():
    result = analyze('budget_alias', max_call_contexts=2)
    helper = named(result, 'long_alias', 'budget_alias')
    assert not any(source.get('container_object') for source in helper.result_sources)
    assert named(result, 'returned.pop').target_status == 'receiver_unresolved'
    assert any(boundary['reason'] == 'container_return_budget'
               and boundary.get('call_id') == helper.id for boundary in result.boundaries)


def test_exact_keyword_and_literal_starred_bindings_preserve_object_identity():
    keyword = analyze('keyword_alias')
    assert object_source(named(keyword, 'identity'))['container_object']['parameter'] == 'mapping'
    assert not sources(named(keyword, 'sink', 'keyword_alias'), 'kwargs')
    expanded = analyze('expanded_alias')
    assert named(expanded, 'returned.pop').target_status == 'local_container_protocol'
    assert all(['out'] in source.get('excluded_paths', [])
               for source in sources(named(expanded, 'sink', 'expanded_alias'), 'kwargs'))


def test_derived_result_uses_element_state_at_its_own_evaluation_point():
    before = analyze('derived_before_clear')
    assert before.trace_parameter('kwargs')['return_paths']
    assert not any(value.get('container_object') for value in before.functions[0]['returns'])
    after = analyze('derived_after_clear')
    assert not after.trace_parameter('kwargs')['return_paths']


@pytest.mark.parametrize('entry,path', [('packed', [0, '*']),
                                      ('packed_mapping', ['payload', '*'])])
def test_contained_alias_materializes_current_elements_with_outer_path(entry, path):
    result = analyze(entry)
    paths = result.trace_parameter('kwargs')['return_paths']
    assert paths and all(value['output_path'] == path for value in paths)
    assert not analyze('packed_cleared').trace_parameter('kwargs')['return_paths']


def test_unmodeled_helper_boundary_includes_opaque_inputs_not_only_known_containers():
    result = analyze('chained_unproven')
    helper = named(result, 'mixed_effects', 'chained_unproven')
    boundary = next(value for value in result.boundaries
                    if value['reason'] == 'container_return_unproven'
                    and value.get('call_id') == helper.id)
    assert boundary['affected_scope'] == 'known'
    assert any(value['name'] == 'kwargs' for value in boundary['affected_values'])


def test_loop_call_merge_does_not_hide_an_unknown_object_alternative():
    result = analyze('loop_unknown')
    helper = named(result, 'identity', 'loop_unknown')
    objects = [value for value in helper.result_sources if value.get('container_object')]
    assert objects and all(value.get('value_incomplete') for value in objects)
    pop = named(result, 'returned.pop', 'loop_unknown')
    assert pop.target_status == 'receiver_unresolved'
    assert any(boundary['reason'] == 'receiver_unresolved'
               and boundary.get('call_id') == pop.id for boundary in result.boundaries)
