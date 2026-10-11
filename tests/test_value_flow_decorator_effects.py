import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
import pcresolve.flow as flow


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_decorator_effects'


def analyze(entry, analyzer=None, depth=1):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='entries', qualname=entry), max_depth=depth)


def decoration(result, entry=None):
    selected = result.entry.qualname if entry is None else entry
    summary = next(item for item in result.functions if item['function']['qualname'] == selected)
    return summary['decorator_effects'][0]


@pytest.mark.parametrize('entry,target', [
    ('pure', 'identity'), ('documented', 'document'), ('conditional', 'conditional_document'),
    ('constructed_factory', 'factory.apply'), ('constructed_instance', 'Document.__call__'),
    ('inherited_instance', 'Document.__call__'), ('super_documented', 'SuperDocument.__call__')])
def test_function_summary_proves_identity_and_body_binding_separately(entry, target):
    result = analyze(entry)
    fact = decoration(result)
    assert fact['function'] == result.to_dict()['entry']
    assert fact['identity_status'] == 'preserved'
    assert fact['body_binding_status'] == 'preserved'
    assert fact['target']['qualname'] == target
    assert fact['expression']['file_path'] == result.entry.file_path
    assert fact['evidence'] and fact['source_hashes'] and fact['assumptions']
    assert fact['completion'] == 'normal_return'
    assert fact['runtime_target_confirmed'] is False
    if entry != 'pure':
        assert any(effect['element_path'] == ['__doc__']
                   and effect['impact'] == 'documentation' for effect in fact['effects'])
    assert not fact['boundaries']
    assert result.to_dict()['functions'][0]['decorator_effects'][0] == fact
    json.dumps(result.to_dict())


@pytest.mark.parametrize('entry,path', [
    ('code_changed', '__code__'), ('alias_code_changed', '__code__'),
    ('indirectly_changed', '__code__'), ('defaults_changed', '__defaults__'),
    ('kwdefaults_changed', '__kwdefaults__')])
def test_same_object_can_have_modified_body_or_binding(entry, path):
    fact = decoration(analyze(entry))
    assert fact['identity_status'] == 'preserved'
    assert fact['body_binding_status'] == 'modified'
    assert any(effect['element_path'] == [path] and effect['impact'] == 'execution_binding'
               for effect in fact['effects'])
    assert fact['boundaries']


def test_signature_metadata_write_is_not_a_body_or_runtime_binding_proof():
    fact = decoration(analyze('signature_changed'))
    assert fact['identity_status'] == 'preserved'
    assert fact['body_binding_status'] == 'unknown'
    assert any(item['impact'] == 'signature_metadata' and item['element_path'] == ['__signature__']
               for item in fact['effects'])


@pytest.mark.parametrize('entry', [
    'unknown_helper', 'captured', 'escaped', 'dynamic_write', 'mixed_return',
    'implicit_return', 'recursive_entry', 'finally_changed', 'unsafe_constructor',
    'custom_lookup', 'method_written', 'rebound_entry', 'stacked'])
def test_no_absence_of_evidence_becomes_preserved_body(entry):
    fact = decoration(analyze(entry))
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']


@pytest.mark.parametrize('entry', ['generator_entry', 'async_entry', 'nested_default',
                                  'nested_annotation', 'conditional_member', 'property_member',
                                  'shadowed_guard', 'factory_annotation', 'renamed', 'conditional_property'])
def test_definition_execution_and_uncertain_instance_lookup_are_not_transparent(entry):
    fact = decoration(analyze(entry))
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']
    if entry in ('generator_entry', 'async_entry'):
        assert fact['identity_status'] == 'unknown'


def test_conditional_write_has_the_source_guard_not_a_runtime_execution_claim():
    fact = decoration(analyze('guarded_code'))
    assert fact['identity_status'] == 'preserved'
    assert fact['body_binding_status'] == 'modified'
    effect = next(item for item in fact['effects'] if item['element_path'] == ['__code__'])
    assert effect['conditions'][0]['test']['source_text'] == 'func.__doc__'
    assert effect['conditions'][0]['branch'] is True


def test_super_uses_actual_instance_mro_not_the_defining_class_mro():
    fact = decoration(analyze('mixed_mro'))
    assert fact['body_binding_status'] == 'modified'
    assert any(item['function']['qualname'] == 'MutationMixin.__call__'
               and item['element_path'] == ['__code__'] for item in fact['effects'])


@pytest.mark.parametrize('entry', ['conditional_state', 'nested_vararg_annotation',
                                  'nested_kwarg_annotation', 'unknown_default_state',
                                  'unknown_factory_default'])
def test_unknown_constructor_branches_and_variadic_annotations_cannot_prove_preservation(entry):
    fact = decoration(analyze(entry))
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']


def test_replacement_does_not_preserve_original_body_binding():
    fact = decoration(analyze('replaced'))
    assert fact['identity_status'] == 'replaced'
    assert fact['body_binding_status'] != 'preserved'


def test_budget_recursion_and_repeated_queries_do_not_leak_proofs(monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = analyze('documented', analyzer)
    saved = original.to_dict()
    assert any(boundary['reason'] == 'decorator_effect_recursion'
               for boundary in decoration(analyze('recursive_entry', analyzer))['boundaries'])
    with monkeypatch.context() as patch:
        patch.setattr(flow, '_DECORATOR_EFFECT_NODE_LIMIT', 1)
        fact = decoration(analyze('documented', analyzer))
        assert fact['body_binding_status'] == 'unknown'
        assert any(item['reason'] == 'decorator_effect_budget' for item in fact['boundaries'])
    assert decoration(analyze('documented', analyzer)) == decoration(original)
    assert original.to_dict() == saved


def test_preserved_fact_can_refine_only_its_own_decoration_boundary():
    result = analyze('Owner.run')
    assert decoration(result)['body_binding_status'] == 'preserved'
    boundary = next(item for item in result.boundaries if item['reason'] == 'decorated_caller_semantics')
    assert boundary['body_binding_status'] == 'preserved'
    assert boundary['boundary_kind'] == 'assumption'
    assert any(item['reason'] == 'dynamic_method_override_possible' for item in result.boundaries)


def test_call_and_expand_use_the_same_exact_function_decoration_facts():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyze('consumer', analyzer)
    call = result.find_calls(callee_name='documented')[0]
    assert call.target.qualname == 'documented'
    assert any(item.get('call_id') == call.id and item['reason'] == 'decorated_target_candidate'
               and item['boundary_kind'] == 'assumption' and item['body_binding_status'] == 'preserved'
               for item in result.boundaries)
    expanded = analyzer.expand(result, call.id)
    assert decoration(expanded, 'documented')['body_binding_status'] == 'preserved'
    assert decoration(analyze('documented', analyzer)) == decoration(expanded, 'documented')
