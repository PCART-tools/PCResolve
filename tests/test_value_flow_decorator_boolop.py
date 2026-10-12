import ast
import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve._decorator_effects import _DecoratorEffects, _data, _data_shapes
import pcresolve.flow as flow


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_decorator_boolop'


def analyze(entry, analyzer=None):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='cases', qualname=entry))


def fact(entry, analyzer=None):
    return analyze(entry, analyzer).functions[0]['decorator_effects'][0]


@pytest.mark.parametrize('entry', [
    'factory_entry', 'empty_doc_entry', 'documented_entry',
    'none_entry', 'empty_entry', 'nonempty_entry',
    'none_argument', 'empty_argument', 'nonempty_argument', 'and_string_entry'])
def test_short_circuit_string_results_preserve_body_binding(entry):
    result = analyze(entry)
    decoration = result.functions[0]['decorator_effects'][0]
    assert decoration['identity_status'] == 'preserved'
    assert decoration['body_binding_status'] == 'preserved'
    assert not decoration['boundaries']
    assert decoration['function'] == result.to_dict()['entry']
    assert decoration['completion'] == 'normal_return'
    assert decoration['basis'] == 'source_snapshot'
    assert decoration['runtime_target_confirmed'] is False
    assert decoration['evidence'] and decoration['source_hashes']
    json.dumps(result.to_dict())


def test_nullable_and_result_is_not_a_string_proof():
    decoration = fact('and_nullable_entry')
    assert decoration['body_binding_status'] == 'unknown'
    assert any(item['reason'] == 'decorator_data_protocol_unproven'
               for item in decoration['boundaries'])


@pytest.mark.parametrize('entry', [
    'skipped_or_entry', 'skipped_and_entry', 'skipped_none_entry',
    'skipped_chain_entry', 'skipped_nested_entry'])
def test_unreachable_operand_calls_are_not_analyzed(entry):
    decoration = fact(entry)
    assert decoration['body_binding_status'] == 'preserved'
    assert not decoration['boundaries']
    assert not any(item['operation'] == 'helper_call' for item in decoration['effects'])


def test_source_known_falsy_helper_result_skips_only_the_later_operand():
    decoration = fact('skipped_helper_result_entry')
    assert decoration['body_binding_status'] == 'preserved'
    assert not decoration['boundaries']
    assert [item['target']['qualname'] for item in decoration['effects']
            if item['operation'] == 'helper_call'] == ['empty_result']


@pytest.mark.parametrize('entry', ['reachable_or_entry', 'reachable_and_entry'])
def test_reachable_unknown_calls_keep_their_boundaries(entry):
    decoration = fact(entry)
    assert decoration['body_binding_status'] == 'unknown'
    assert any(item['reason'] == 'decorator_call_unresolved'
               for item in decoration['boundaries'])
    assert any(item['reason'] == 'decorator_object_escape'
               for item in decoration['boundaries'])


@pytest.mark.parametrize('entry,branch', [
    ('conditional_or_entry', False), ('conditional_and_entry', True),
    ('conditional_chain_entry', False)])
def test_unknown_reachability_retains_operand_effect_conditions(entry, branch):
    decoration = fact(entry)
    assert decoration['body_binding_status'] == 'unknown'
    issue = next(item for item in decoration['boundaries']
                 if item['reason'] == 'decorator_call_unresolved')
    assert issue['conditions'][0]['test']['source_text'] == 'function.__doc__'
    assert issue['conditions'][0]['branch'] is branch


def test_unknown_truth_protocol_is_not_proven_by_a_literal_fallback():
    decoration = fact('unknown_truth_entry')
    assert decoration['body_binding_status'] == 'unknown'
    assert any(item['reason'] == 'decorator_truth_protocol_unproven'
               for item in decoration['boundaries'])


def test_unknown_or_result_does_not_gain_string_shape():
    decoration = fact('unknown_result_entry')
    assert decoration['body_binding_status'] == 'unknown'
    assert any(item['reason'] == 'decorator_data_protocol_unproven'
               for item in decoration['boundaries'])


def test_custom_truth_protocol_keeps_a_boundary():
    decoration = fact('custom_truth_entry')
    assert decoration['body_binding_status'] == 'unknown'
    assert any(item['reason'] == 'decorator_truth_protocol_unproven'
               for item in decoration['boundaries'])
    assert any(item['reason'] == 'decorator_data_protocol_unproven'
               for item in decoration['boundaries'])


def test_function_operand_keeps_an_operation_boundary():
    decoration = fact('function_operand_entry')
    assert decoration['body_binding_status'] == 'unknown'
    assert any(item['reason'] == 'decorator_operation_unproven'
               for item in decoration['boundaries'])


def test_conditional_doc_updates_join_only_reachable_object_states():
    decoration = fact('conditional_fill_entry')
    assert decoration['body_binding_status'] == 'preserved'
    helper = next(item for item in decoration['effects'] if item['operation'] == 'helper_call')
    assert helper['target']['qualname'] == 'fill_empty'
    assert helper['conditions'][0]['branch'] is False
    write = next(item for item in decoration['effects']
                 if item['function']['qualname'] == 'fill_empty')
    assert write['conditions'][0]['branch'] is False
    nullable = fact('conditional_none_entry')
    assert nullable['body_binding_status'] == 'unknown'
    assert any(item['reason'] == 'decorator_data_protocol_unproven'
               for item in nullable['boundaries'])


def test_conditionally_reachable_code_write_is_not_filtered():
    decoration = fact('conditional_code_entry')
    assert decoration['body_binding_status'] == 'modified'
    effect = next(item for item in decoration['effects'] if item['impact'] == 'execution_binding')
    assert effect['conditions'][0]['test']['source_text'] == 'function.__doc__'
    assert effect['conditions'][0]['branch'] is False


def test_queries_and_expand_keep_the_exact_entry_proof():
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = analyze('factory_entry', analyzer)
    decoration = original.functions[0]['decorator_effects'][0]
    assert decoration['body_binding_status'] == 'preserved'
    assert fact('unknown_result_entry', analyzer)['body_binding_status'] == 'unknown'
    assert fact('factory_entry', analyzer) == decoration
    assert all(item['boundary_kind'] == 'assumption' for item in original.boundaries
               if item['reason'] == 'decorated_caller_semantics')
    call = original.find_calls(callee_name='fixed')[0]
    assert call.target.qualname == 'fixed'
    assert call.argument_sources[0]['sources']
    expanded = analyzer.expand(original, call.id)
    assert expanded.functions[0]['decorator_effects'][0] == decoration


@pytest.mark.parametrize('expression,shape,expected', [
    ('value or ""', 'str', {'str'}),
    ('value or ""', 'str_or_none', {'str'}),
    ('value and ""', 'str', {'str'}),
    ('value and ""', 'str_or_none', {'str', 'NoneType'}),
    ('value or None', 'str', {'str', 'NoneType'}),
    ('value and None', 'str', {'str', 'NoneType'}),
    ('value or ""', 'int', {'str', 'int'}),
    ('value and ""', 'int', {'str', 'int'}),
    ('value or ""', 'NoneType', {'str'}),
    ('value and ""', 'NoneType', {'NoneType'}),
    ('value or ""', None, set()),
    ('value and ""', None, set())])
def test_boolop_joins_possible_operand_shapes_without_promoting_unknowns(expression, shape, expected):
    analyzer = FlowAnalyzer(project_root=ROOT)
    analyzer._index()
    target = analyzer._definition_index.find('cases', 'fixed')[0]
    proof = _DecoratorEffects(analyzer, target,
        lambda ref, node: {'source_text': ast.unparse(node), 'lineno': node.lineno}, 2000)
    value = _data() if shape is None else dict(_data(), python_shape=shape)
    result = proof.expression(ast.parse(expression, mode='eval').body, {'value': value}, target)
    assert _data_shapes(result) == expected
    assert bool(proof.boundaries) is (shape is None)


def test_short_circuit_proof_remains_bounded(monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = fact('factory_entry', analyzer)
    with monkeypatch.context() as patch:
        patch.setattr(flow, '_DECORATOR_EFFECT_NODE_LIMIT', 5)
        bounded = fact('factory_entry', analyzer)
        assert bounded['body_binding_status'] == 'unknown'
        assert any(item['reason'] == 'decorator_effect_budget' for item in bounded['boundaries'])
    assert fact('factory_entry', analyzer) == original
