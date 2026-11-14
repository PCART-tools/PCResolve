import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from tests.flow_test_support import set_decorator_effect_limit
import pcresolve.flow.analyzer as flow
import pcresolve.flow.analysis.proof_context as flow_proof_context


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_decorator_documents'


def decoration(entry, analyzer=None):
    result = (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='entries', qualname=entry))
    return result.functions[0]['decorator_effects'][0]


@pytest.mark.parametrize('entry', ['source_method', 'source_function'])
def test_source_function_documentation_supplies_bounded_constructor_data(entry):
    fact = decoration(entry)
    assert fact['identity_status'] == fact['body_binding_status'] == 'preserved'
    assert not fact['boundaries']
    assert not any(item.get('target', {}).get('qualname') == 'unknown_indent'
                   for item in fact['effects'] if isinstance(item.get('target'), dict))
    binding = fact['construction']['parameter_bindings'][0]
    assert binding['value_provenance']['kind'] == 'source_function_documentation'
    assert binding['value_provenance']['function']['module'] == 'documents'
    assert str(ROOT / 'documents.py') in fact['source_hashes']
    assert fact['runtime_target_confirmed'] is False
    json.dumps(fact)


def test_known_constructor_comparison_selects_only_the_reachable_state():
    fact = decoration('unchanged_defaults')
    assert fact['body_binding_status'] == 'preserved'
    assert not fact['boundaries']
    assert decoration('changed_defaults')['body_binding_status'] == 'modified'
    assert decoration('uncertain_defaults')['body_binding_status'] != 'preserved'


@pytest.mark.parametrize('entry', ['changed_document', 'reachable_helper', 'opaque_argument',
                                  'custom_class_lookup', 'inherited_custom_lookup', 'decorated_source'])
def test_unproven_document_sources_and_reachable_helpers_retain_boundaries(entry):
    fact = decoration(entry)
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']


def test_document_proof_budget_and_queries_do_not_leak_source_values(monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    saved = decoration('source_method', analyzer)
    assert saved['body_binding_status'] == 'preserved'
    with monkeypatch.context() as patch:
        set_decorator_effect_limit(patch, 1)
        assert decoration('source_method', analyzer)['body_binding_status'] == 'unknown'
    assert decoration('reachable_helper', analyzer)['body_binding_status'] != 'preserved'
    assert decoration('source_method', analyzer) == saved


@pytest.mark.parametrize('entry', ['normalized_method', 'normalized_empty'])
def test_fresh_scalar_normalization_and_finite_builtin_join_have_effect_facts(entry):
    fact = decoration(entry)
    assert fact['body_binding_status'] == 'preserved'
    assert not fact['boundaries']
    assert fact['construction']['lifetime'] == 'single_decoration'
    write = next(effect for effect in fact['effects'] if effect['target'] == 'decorator_instance')
    assert write['operation'] == 'attribute_write' and write['impact'] == 'data_only'
    assert write['element_path'] == ['text']
    assert write['after_shapes'] == ['str']
    join = next(effect for effect in fact['effects'] if effect['target'] == 'str.join')
    assert join['operation'] == 'builtin_call' and join['impact'] == 'data_only'
    assert join['receiver_shape'] == 'str'
    assert join['element_shapes'] == [['str'], ['str']]


@pytest.mark.parametrize('entry', ['shared_normalization', 'unknown_normalization',
                                  'escaping_normalization', 'unknown_join', 'unavailable_cleaner'])
def test_scalar_normalization_does_not_hide_unknown_state_lifetimes_or_calls(entry):
    fact = decoration(entry)
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']


def test_normalization_branches_join_receiver_state_before_later_execution_guards():
    fact = decoration('conditional_mutation')
    assert fact['body_binding_status'] == 'modified'
    assert any(item['element_path'] == ['__defaults__'] for item in fact['effects'])
