import copy
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures/value_flow_with_nested_rhs'
REASON = 'context_exit_nested_expression_unmodeled'


def analyze(name, analyzer=None):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='cases', qualname=name), max_depth=3)


def exits(result):
    return [call for call in result.calls if call.implicit_protocol.get('method') == '__exit__']


@pytest.mark.parametrize('name', [
    'tuple_missing_pop', 'list_missing_pop', 'dict_missing_pop',
    'annotated_tuple_pop', 'annotated_list_pop', 'annotated_dict_pop',
    'return_nested_pop', 'expression_nested_pop', 'deep_nested_pop',
    'dict_key_nested_pop', 'nested_default_pop',
])
def test_container_call_evaluation_cannot_publish_a_complete_exit_proof(name):
    result = analyze(name)
    boundaries = [boundary for boundary in result.boundaries if boundary['reason'] == REASON]
    assert boundaries
    assert all(boundary['function']['qualname'] == name + '.Exit.__exit__'
               and boundary['affected_scope'] == 'unknown'
               and "pop('missing'" in boundary['evidence']['source_text'] for boundary in boundaries)
    assert exits(result)
    assert all(call.implicit_protocol['completion'] == 'unconfirmed' for call in exits(result))
    assert any(boundary['reason'] == 'context_exit_unmodeled'
               and REASON in boundary['issues']
               and boundary['call_id'] in {call.id for call in exits(result)}
               and boundary['function'] == result.to_dict()['entry'] for boundary in result.boundaries)
    payload = result.to_dict()
    assert payload['schema_version'] == 'flow-0.2'
    assert any(boundary['reason'] == REASON for boundary in payload['boundaries'])


def test_unmodeled_nested_mutation_does_not_publish_strong_caller_contents():
    result = analyze('sequential_mutations')
    assert any(boundary['reason'] == REASON for boundary in result.boundaries)
    paths = result.trace_parameter('kwargs')['return_paths']
    assert paths and all(['out'] not in path.get('excluded_paths', []) for path in paths)
    assert all(call.implicit_protocol['completion'] == 'unconfirmed' and not call.effects
               for call in exits(result))


@pytest.mark.parametrize('name', ['pure_literal_rhs', 'pure_data_rhs', 'unreachable_nested_pop'])
def test_call_free_or_unreachable_container_construction_keeps_existing_proof(name):
    result = analyze(name)
    assert result.find_calls(callee_name='fixed')[0].analysis_status == 'analyzed'
    assert not any(boundary['reason'] in (REASON, 'context_exit_unmodeled') for boundary in result.boundaries)
    assert exits(result) and all(call.implicit_protocol['completion'] == 'source_modeled'
        and call.implicit_protocol['exit_outcomes'] == [{'kind': 'normal', 'exception': None}]
        for call in exits(result))


def test_guard_does_not_change_ordinary_container_expression_facts():
    result = analyze('ordinary_nested_pop')
    assert not any(boundary['reason'] == REASON for boundary in result.boundaries)
    assert result.find_calls(callee_name='kwargs.pop')[0].target_status == 'local_container_protocol'
    assert result.trace_parameter('kwargs')['return_paths']


def test_nested_completion_boundaries_do_not_pollute_later_queries_or_expand():
    analyzer = FlowAnalyzer(project_root=ROOT)
    pure = analyze('pure_literal_rhs', analyzer)
    before = copy.deepcopy(pure.to_dict())
    nested = analyze('tuple_missing_pop', analyzer)
    assert analyze('pure_literal_rhs', analyzer).to_dict() == before
    expanded = analyzer.expand(nested, exits(nested)[0].id)
    assert nested.to_dict() == analyze('tuple_missing_pop', analyzer).to_dict()
    assert any(boundary['reason'] == REASON for boundary in expanded.boundaries)
