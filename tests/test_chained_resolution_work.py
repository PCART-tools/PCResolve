## @package tests.test_chained_resolution_work
#  Query-local expression reuse must preserve lexical ownership evidence.

import ast
from pathlib import Path

import pytest

from pcresolve import SingleFileAnalyzer, analyze_project


ROOT = Path(__file__).parent / 'fixtures' / 'chained_resolution_work'


@pytest.mark.parametrize('query', ['_expression_container_shape', '_resolve_methods'])
def test_unknown_method_chain_does_not_repeat_inner_shape_queries(monkeypatch, query):
    analyzer = SingleFileAnalyzer()
    node = ast.parse('factory()' + '.next()' * 7).body[0].value
    calls = []
    original = analyzer._call_container_shape

    def record(node):
        calls.append(node)
        return original(node)

    monkeypatch.setattr(analyzer, '_call_container_shape', record)
    result = getattr(analyzer, query)(node)
    assert result == ('', '') if query == '_expression_container_shape' else result is None
    assert len(calls) <= 16


def test_independent_queries_observe_rebinding_and_scope_changes():
    analyzer = SingleFileAnalyzer()
    node = ast.parse('value.copy()').body[0].value
    analyzer.current_scope().bind('value', 'python', container_kind='dict')
    assert analyzer._expression_container_shape(node) == ('dict', '')
    analyzer.current_scope().bind('value', 'python', container_kind='list')
    assert analyzer._expression_container_shape(node) == ('list', '')
    analyzer.push_scope('function', 'inner')
    analyzer.current_scope().bind('value', 'python', container_kind='set')
    assert analyzer._expression_container_shape(node) == ('set', '')
    analyzer.pop_scope()
    assert analyzer._expression_container_shape(node) == ('list', '')


def test_unresolved_chain_keeps_unknown_and_independent_import_owner():
    result = analyze_project(str(ROOT))
    chain = [call for call in result.all_api_calls if call.expression.endswith('.seventh()')]
    assert len(chain) == 1 and chain[0].top_library == 'unknown'
    parsed = [call for call in result.all_api_calls if call.expression == "json.loads('{}')"]
    assert len(parsed) == 1 and parsed[0].top_library == 'json'
