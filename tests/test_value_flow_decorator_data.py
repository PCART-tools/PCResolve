import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
import pcresolve.flow as flow


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_decorator_data'


def analyze(entry, analyzer=None):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='cases', qualname=entry))


def fact(entry, analyzer=None):
    result = analyze(entry, analyzer)
    return result.functions[0]['decorator_effects'][0]


@pytest.mark.parametrize('entry', ['documented', 'inherited', 'calculated_entry'])
def test_source_document_data_and_cache_effects_preserve_function_binding(entry):
    decoration = fact(entry)
    assert decoration['identity_status'] == 'preserved'
    assert decoration['body_binding_status'] == 'preserved'
    assert not decoration['boundaries']
    assert decoration['basis'] == 'source_snapshot'
    assert decoration['completion'] == 'normal_return'
    assert decoration['runtime_target_confirmed'] is False
    assert decoration['source_hashes']
    assert any(item['impact'] == 'documentation' for item in decoration['effects'])
    if entry != 'calculated_entry':
        effect = next(item for item in decoration['effects'] if item['operation'] == 'setdefault')
        assert effect['target'] == 'documentation_cache'
        assert effect['method_binding']['builtin'] == 'dict.setdefault'
        assert effect['element_path'] == ['*']
        assert effect['insertion'] == 'conditional'
        assert effect['completion'] == 'normal_return'
        assert effect['conditions']
        assert isinstance(effect['object_source'], str)
        assert effect['conditions'][-1]['mapping_membership']['object_source'] == effect['object_source']
        assert any(item['source_text'] == "return text" for item in decoration['evidence'])
    json.dumps(decoration)


@pytest.mark.parametrize('entry', [
    'overridden', 'custom_lookup', 'custom_item', 'written', 'dynamic_written',
    'unknown_base', 'custom_new', 'escaping_cache', 'stateful_cache',
    'opaque_entry', 'unknown_format_entry', 'escaped_entry', 'signature_entry',
    'opaque_default', 'recursive_entry', 'annotated_cache', 'joined_entry'])
def test_unproven_lookup_or_function_escape_does_not_prove_preservation(entry):
    decoration = fact(entry)
    assert decoration['body_binding_status'] != 'preserved'
    assert decoration['boundaries']


@pytest.mark.parametrize('entry,path', [('code_entry', '__code__'),
                                       ('defaults_entry', '__defaults__'),
                                       ('kwdefaults_entry', '__kwdefaults__')])
def test_helper_execution_binding_writes_are_not_documentation_effects(entry, path):
    decoration = fact(entry)
    assert decoration['body_binding_status'] == 'modified'
    assert any(item['target'] == 'input_function' and item['element_path'] == [path]
               for item in decoration['effects'])


def test_inherited_builtin_method_has_source_binding_not_builtin_object_shape():
    result = analyze('Cache.__missing__')
    call = result.find_calls(callee_name='self.setdefault')[0]
    proof = next(item for item in call.receiver_type_evidence
                 if item.get('kind') == 'builtin_method_binding')
    assert proof['builtin'] == 'dict.setdefault'
    assert proof['status'] == 'source_bound'
    assert proof['runtime_target_confirmed'] is False
    assert call.target is None and not call.target_candidates
    effect = next(item for item in call.effects if item['operation'] == 'setdefault')
    assert effect['element_path'] == ['*'] and effect['status'] == 'unknown_key'
    assert effect['completion'] == 'normal_return'
    assert not any(value.get('container_object') for value in call.result_sources)
    assert any(item.get('call_id') == call.id and item['reason'] == 'dynamic_method_override_possible'
               for item in result.boundaries)
    assert result.find_calls(callee_name='clean_text')[0].target.qualname == 'clean_text'


def test_unknown_parameter_is_not_promoted_to_builtin_dict():
    call = analyze('ordinary_unknown').find_calls(callee_name='mapping.setdefault')[0]
    assert call.target_status == 'receiver_unresolved'
    assert not call.effects and not call.receiver_type_evidence


@pytest.mark.parametrize('module', ['shadowed', 'rebound', 'escaped_class',
                                  'written_method_alias', 'mixed_class_alias', 'external_base',
                                  'instance_written', 'dynamic_instance_written'])
def test_unconfirmed_base_or_class_escape_cannot_prove_inherited_method(module):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef(module=module, qualname='Cache.__missing__'))
    call = result.find_calls(callee_name='self.setdefault')[0]
    assert call.target_status == 'receiver_unresolved'
    assert not call.receiver_type_evidence and not call.effects


def test_stable_import_alias_preserves_source_hierarchy():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef(module='aliased', qualname='entry'))
    decoration = result.functions[0]['decorator_effects'][0]
    assert decoration['body_binding_status'] == 'preserved'
    assert any(effect.get('class', {}).get('module') == 'aliased' for effect in decoration['effects'])


def test_budget_and_query_contexts_do_not_reuse_partial_cache_proof(monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = fact('documented', analyzer)
    assert original['body_binding_status'] == 'preserved'
    assert fact('overridden', analyzer)['body_binding_status'] == 'unknown'
    with monkeypatch.context() as patch:
        patch.setattr(flow, '_DECORATOR_EFFECT_NODE_LIMIT', 5)
        assert fact('documented', analyzer)['body_binding_status'] == 'unknown'
    assert fact('documented', analyzer) == original


def test_inherited_method_scan_budget_is_an_explicit_boundary(monkeypatch):
    monkeypatch.setattr(flow, '_CLASS_BINDING_NODE_LIMIT', 1)
    result = analyze('Cache.__missing__')
    call = result.find_calls(callee_name='self.setdefault')[0]
    assert not call.effects and not call.receiver_type_evidence
    assert any(item.get('call_id') == call.id and item['reason'] == 'class_binding_budget'
               for item in result.boundaries)
    decoration = fact('documented')
    assert decoration['body_binding_status'] == 'unknown'
    assert any(item['reason'] == 'decorator_effect_budget' for item in decoration['boundaries'])


def test_unknown_default_expression_is_analyzed_before_conditional_cache_insertion():
    decoration = fact('opaque_default')
    issue = next(item for item in decoration['boundaries']
                 if item['evidence']['source_text'] == 'unknown_default(key)')
    effect = next(item for item in decoration['effects'] if item['operation'] == 'setdefault')
    assert issue['function']['qualname'] == 'OpaqueDefaultCache.__missing__'
    assert effect['insertion'] == 'conditional'
    assert decoration['body_binding_status'] == 'unknown'


def test_recursive_data_helper_retains_explicit_recursion_issue():
    assert any(item['reason'] == 'decorator_effect_recursion'
               for item in fact('recursive_entry')['boundaries'])
