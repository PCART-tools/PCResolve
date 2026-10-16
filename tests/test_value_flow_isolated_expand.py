## @package tests.test_value_flow_isolated_expand

from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_isolated_expand'


def test_recursive_edge_can_expand_without_merging_the_open_entry_context():
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = analyzer.analyze(FunctionRef('cases', 'recursive'))
    before = original.to_dict()
    edge = original.find_calls(callee_name='recursive')[0]
    child = analyzer.expand(original, edge.id, isolate=True)
    call = child.find_calls(callee_name='metric')[0]
    assert call.target_status == 'bounded_alternatives'
    assert {item['qualname'] for item in call.target_candidates} == {'fixed', 'accepts'}
    assert child.inputs['expansion_context']['incoming_call_id'] == edge.id
    assert all(item['incoming_call_id'] == edge.id for item in call.analysis_contexts)
    assert original.to_dict() == before
    assert analyzer.expand(original, edge.id).to_dict() != child.to_dict()


def test_separate_call_edges_do_not_share_callable_targets():
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = analyzer.analyze(FunctionRef('cases', 'mixed'), max_depth=2)
    edges = original.find_calls(callee_name='invoke')
    for edge, expected in zip(edges, ('accepts', 'fixed')):
        child = analyzer.expand(original, edge.id, isolate=True)
        call = child.find_calls(callee_name='metric')[0]
        assert call.target.qualname == expected
        assert all(item['incoming_call_id'] == edge.id for item in call.analysis_contexts)


def test_isolation_keeps_recursion_boundary_and_validates_arguments():
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = analyzer.analyze(FunctionRef('cases', 'loop'))
    edge = original.find_calls(callee_name='loop')[0]
    child = analyzer.expand(original, edge.id, additional_depth=3, isolate=True)
    assert any(item['reason'] == 'recursion' for item in child.boundaries)
    assert not child.find_calls(callee_name='metric')
    with pytest.raises(ValueError, match='bool'):
        analyzer.expand(original, edge.id, isolate='yes')


def test_unknown_incoming_callable_does_not_become_a_closed_target():
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = analyzer.analyze(FunctionRef('cases', 'loop'))
    child = analyzer.expand(original, original.find_calls(callee_name='loop')[0].id, isolate=True)
    assert all(not value.get('callable_type') for values in child.inputs[
        'expansion_context']['parameter_facts'].values() for value in values)
