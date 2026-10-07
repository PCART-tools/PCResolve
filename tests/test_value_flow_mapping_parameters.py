## @package tests.test_value_flow_mapping_parameters

from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_mapping_parameters'


def analyze(entry, analyzer=None, **limits):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='cases', qualname=entry),
        max_depth=limits.pop('max_depth', 3), **limits)


def named(result, name, entry):
    return next(call for call in result.find_calls(callee_name=name)
                if call.caller.qualname == entry)


def parameter_sources(call, parameter='kwargs'):
    return [value for argument in call.argument_sources
            for value in argument['sources']
            if value['kind'] == 'parameter' and value['source'] == parameter]


def removal(call):
    return next(effect for effect in call.effects
                if effect['kind'] == 'mapping_element')


@pytest.mark.parametrize('entry,helper,operation', [
    ('root_inplace', 'remove_out', 'pop'),
    ('root_delete', 'delete_out', 'delete'),
    ('root_alias', 'alias_remove', 'pop'),
    ('root_alias_delete', 'alias_delete', 'delete')])
def test_ordinary_parameter_removal_updates_open_caller_object(entry, helper, operation):
    result = analyze(entry)
    call = named(result, helper, entry)
    effect = removal(call)
    assert effect['operation'] == operation
    assert effect['element_path'] == ['out']
    assert effect['state_after'] == 'absent'
    assert effect['completion'] == 'normal_return'
    assert any(root['name'] == 'kwargs' for root in effect['mapping'])
    assert effect['binding']['parameter'] == 'mapping'
    assert effect['binding']['argument'] == {'position': 0}
    assert effect['evidence'] and effect['call_evidence']['source_text']
    assert effect in [dict(value, kind='mapping_element')
                      for value in result.functions[0]['mapping_effects']]
    downstream = named(result, 'fixed' if entry == 'root_inplace' else 'sink', entry)
    remaining = parameter_sources(downstream)
    assert remaining and all(value.get('output_path') == ['*'] for value in remaining)
    assert all(['out'] in value.get('excluded_paths', []) for value in remaining)
    if operation == 'pop':
        inner = named(result, 'mapping.pop' if helper == 'remove_out' else 'alias.pop', helper)
        assert inner.target is None and not inner.target_candidates
        assert inner.target_status == 'receiver_unresolved'


def test_mutation_then_return_alias_materializes_current_object():
    result = analyze('root_return')
    call = named(result, 'clean', 'root_return')
    assert removal(call)['element_path'] == ['out']
    assert call.result_sources[0]['container_object']['identity'] == 'argument_alias'
    assert all(['out'] in value.get('excluded_paths', [])
               for value in parameter_sources(named(result, 'fixed', 'root_return')))
    evidence = {value.get('source_text') for value in call.result_sources[0]['evidence']}
    assert "mapping.pop('out', None)" in evidence and 'return mapping' in evidence


@pytest.mark.parametrize('entry', ['root_return_alias', 'root_return_delete', 'returned_input'])
def test_original_and_returned_reads_observe_same_updated_object(entry):
    result = analyze(entry)
    paths = result.trace_parameter('kwargs')['return_paths']
    assert paths and {value['output_path'][0] for value in paths} == {0, 1}
    assert all([value['output_path'][0], 'out'] in value.get('excluded_paths', [])
               for value in paths)


def test_clear_of_modified_returned_alias_does_not_restore_original_contents():
    result = analyze('root_clear')
    assert named(result, 'forwarded.clear', 'root_clear').target_status == 'local_container_protocol'
    assert not result.trace_parameter('kwargs')['return_paths']


def test_finite_dict_and_independent_allocations_do_not_become_open_or_share_ids():
    result = analyze('finite')
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']
    remaining = parameter_sources(named(result, 'sink', 'finite'), 'y')
    assert remaining and all(value['output_path'] == ['keep'] for value in remaining)
    two = analyze('two_inputs')
    assert not two.trace_parameter('x')['return_paths']
    assert {value['output_path'][0] for value in two.trace_parameter('y')['return_paths']} == {0, 1}
    repeated = analyze('repeated_calls')
    calls = [call for call in repeated.find_calls(callee_name='clean')
             if call.caller.qualname == 'repeated_calls']
    assert len({call.result_sources[0]['container_object']['source'] for call in calls}) == 2
    assert {value['output_path'][0] for value in repeated.trace_parameter('x')['return_paths']} == {1}
    assert {value['output_path'][0] for value in repeated.trace_parameter('y')['return_paths']} == {0}


@pytest.mark.parametrize('entry', ['keyword_binding', 'expanded_binding'])
def test_exact_bindings_apply_symbolic_effect(entry):
    result = analyze(entry)
    call = named(result, 'remove_out', entry)
    assert removal(call)['binding']['parameter'] == 'mapping'
    assert all(['out'] in value.get('excluded_paths', [])
               for value in parameter_sources(named(result, 'sink', entry)))


@pytest.mark.parametrize('entry,helper', [
    ('root_required', 'required_pop'), ('root_delete', 'delete_out')])
def test_required_key_effect_is_only_a_normal_completion_fact(entry, helper):
    result = analyze(entry)
    call = named(result, helper, entry)
    effect = removal(call)
    assert effect['completion'] == 'normal_return'
    assert effect['may_raise'] == 'KeyError'
    assert any(value['reason'] == 'mapping_effect_exception_path'
               and value.get('call_id') == call.id for value in result.boundaries)


@pytest.mark.parametrize('entry', ['catch_required', 'catch_delete'])
def test_caller_exception_handler_cannot_use_normal_path_strong_update(entry):
    result = analyze(entry)
    sources = parameter_sources(named(result, 'sink', entry))
    assert sources and any(['out'] not in value.get('excluded_paths', []) for value in sources)
    assert any(value['reason'] == 'mapping_effect_exception_path' for value in result.boundaries)


def test_returned_pop_value_is_not_a_container_alias():
    result = analyze('root_popped')
    call = named(result, 'popped', 'root_popped')
    assert removal(call)['element_path'] == ['out']
    assert not any(value.get('container_object') for value in call.result_sources)
    assert named(result, 'value.clear', 'root_popped').target_status == 'receiver_unresolved'
    paths = result.trace_parameter('kwargs')['return_paths']
    assert any(value['output_path'][0] == 1 for value in paths)
    assert all([0, 'out'] in value.get('excluded_paths', [])
               for value in paths if value['output_path'][0] == 0)


def test_popped_value_uses_pre_removal_elements_not_already_excluded_key():
    assert analyze('root_popped_finite').trace_parameter('value')['return_paths']
    assert not analyze('root_repeated_pop').trace_parameter('kwargs')['return_paths']


@pytest.mark.parametrize('entry', ['root_recapture', 'root_copy'])
def test_fresh_capture_or_copy_does_not_mutate_original(entry):
    result = analyze(entry)
    helper = named(result, 'recapture' if entry == 'root_recapture' else 'copied', entry)
    assert not helper.effects
    assert not any(value.get('container_object') for value in helper.result_sources)
    sources = parameter_sources(named(result, 'sink', entry))
    assert sources and not any(['out'] in value.get('excluded_paths', []) for value in sources)


@pytest.mark.parametrize('entry,helper', [
    ('negative_key', 'dynamic_key'), ('negative_conditional', 'conditional'),
    ('negative_write', 'unknown_write'), ('negative_escape', 'escaping'),
    ('negative_recursive', 'recursive'), ('negative_caught', 'caught'),
    ('mixed_binding', 'remove_out'), ('uncertain_binding', 'remove_out'),
    ('modified_callable', 'clean'), ('negative_decorator', 'decorated')])
def test_unproven_helper_never_applies_a_partial_strong_update(entry, helper):
    result = analyze(entry)
    call = named(result, helper, entry)
    assert not call.effects
    assert not any(value.get('container_object') for value in call.result_sources)
    remaining = parameter_sources(named(result, 'sink', entry))
    assert remaining and any(['out'] not in value.get('excluded_paths', []) for value in remaining)
    assert any(value['reason'] == 'mapping_effect_unproven'
               and value.get('call_id') == call.id for value in result.boundaries)


@pytest.mark.parametrize('entry,helper', [('negative_generator', 'generator'),
                                         ('negative_loop', 'loop_keys')])
def test_generator_and_finite_key_loop_are_not_executed_as_straight_line_effects(entry, helper):
    result = analyze(entry)
    assert not named(result, helper, entry).effects
    assert any(value['reason'] == 'mapping_effect_unproven'
               for value in result.boundaries)


def test_unknown_effect_after_known_removal_cannot_reuse_a_final_absence_fact():
    result = analyze('unknown_after_removal')
    assert removal(named(result, 'remove_out', 'unknown_after_removal'))['state_after'] == 'absent'
    unknown = named(result, 'escaping', 'unknown_after_removal')
    assert not unknown.effects
    assert any(['out'] not in value.get('excluded_paths', [])
               for value in parameter_sources(named(result, 'sink', 'unknown_after_removal')))


def test_known_non_dict_shape_does_not_satisfy_symbolic_dict_constraint():
    result = analyze('mismatched_shape')
    helper = named(result, 'remove_out', 'mismatched_shape')
    assert not helper.effects
    assert result.trace_parameter('value')['return_paths']
    assert any(value['reason'] == 'mapping_effect_unproven'
               and value.get('call_id') == helper.id for value in result.boundaries)


@pytest.mark.parametrize('entry', ['remove_out', 'delete_out', 'alias_remove',
                                 'unknown_receiver', 'annotated_receiver'])
def test_generic_helper_and_unknown_receiver_have_no_invented_builtin_shape(entry):
    result = analyze(entry)
    assert not any(value['kind'] == 'mapping_element' for call in result.calls for value in call.effects)
    assert not result.functions[0]['mapping_effects']
    assert result.boundaries


def test_multiple_known_objects_and_caller_branch_do_not_get_unconditional_updates():
    multiple = analyze('two_known')
    assert not named(multiple, 'remove_out', 'two_known').effects
    assert multiple.trace_parameter('x')['return_paths'] and multiple.trace_parameter('y')['return_paths']
    branch = analyze('in_caller_branch')
    effect = removal(named(branch, 'remove_out', 'in_caller_branch'))
    assert effect['state_after'] == 'conditional' and effect['conditions']
    assert any(['out'] not in value.get('excluded_paths', [])
               for value in parameter_sources(named(branch, 'sink', 'in_caller_branch')))


def test_budget_and_cache_are_symbolic_and_snapshot_safe():
    result = analyze('negative_budget', max_call_contexts=2)
    helper = named(result, 'limited', 'negative_budget')
    assert not helper.effects
    assert any(value['reason'] == 'mapping_effect_budget' and value.get('call_id') == helper.id
               for value in result.boundaries)
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyze('root_return', analyzer, max_depth=1)
    snapshot = first.to_dict()
    analyze('repeated_calls', analyzer)
    repeated = analyze('root_return', analyzer, max_depth=1)
    assert first.to_dict() == snapshot == repeated.to_dict()
    expanded = analyzer.expand(first, named(first, 'clean', 'root_return').id)
    assert first.to_dict() == snapshot
    assert removal(named(expanded, 'clean', 'root_return'))['element_path'] == ['out']


def test_cross_module_alias_keeps_effect_binding_return_and_source_evidence():
    result = analyze('cross_module')
    helper = named(result, 'imported_clean', 'cross_module')
    effect = removal(helper)
    assert effect['evidence'][0]['file_path'].endswith('helpers.py')
    assert helper.target.module == 'helpers'
    assert helper.result_sources[0]['container_object']['identity'] == 'argument_alias'
    assert {value['output_path'][0] for value in result.trace_parameter('kwargs')['return_paths']} == {0, 1}


def test_repeated_unknown_context_keeps_only_a_partial_effect_fact():
    result = analyze('loop_unknown')
    call = named(result, 'clean', 'loop_unknown')
    effect = removal(call)
    assert effect['state_after'] == 'conditional'
    assert effect['status'] == 'partial_context'
    assert any(value['reason'] == 'mapping_effect_unproven'
               and value.get('call_id') == call.id for value in result.boundaries)
    assert any(['out'] not in value.get('excluded_paths', [])
               for value in parameter_sources(named(result, 'sink', 'loop_unknown')))


@pytest.mark.parametrize('entry,helper', [('modified_clear_return', 'clear_return'),
                                         ('root_capture_clear', 'capture_clear')])
def test_existing_clear_cannot_bypass_callable_or_fresh_capture_guards(entry, helper):
    result = analyze(entry)
    assert not named(result, helper, entry).effects
    assert parameter_sources(named(result, 'sink', entry))


def test_empty_object_still_has_mapping_identity_root_for_effect_and_boundary():
    empty = analyze('empty_mapping_root')
    assert any(value['name'] == 'kwargs'
               for value in removal(named(empty, 'remove_out', 'empty_mapping_root'))['mapping'])
    unknown = analyze('unknown_empty_mapping_root')
    helper = named(unknown, 'escaping', 'unknown_empty_mapping_root')
    boundary = next(value for value in unknown.boundaries
                    if value['reason'] == 'mapping_effect_unproven'
                    and value.get('call_id') == helper.id)
    assert any(value['name'] == 'kwargs' for value in boundary['affected_values'])
