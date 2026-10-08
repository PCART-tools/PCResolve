## @package tests.test_recursive_method_dispatch
#  Receiver target matching must terminate before call-context construction.

import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef, ProjectAnalyzer, analyze_project
from pcresolve.sources import PythonShape, SourceSet


ROOT = Path(__file__).parent / 'fixtures' / 'recursive_method_dispatch'


def test_recursive_peer_receiver_does_not_overflow_single_file_analysis():
    result = analyze_project(str(ROOT / 'main.py'))
    calls = {call.expression: call for call in result.all_api_calls}
    assert calls['other.equals(self)'].top_library == 'unknown'
    assert calls['self._concat(other)'].top_library == 'local'
    assert calls['self._concat_same_dtype(other)'].top_library == 'local'
    assert calls['json.loads(value)'].top_library == 'json'


def test_recursive_target_guard_is_reset_between_analysis_runs():
    analyzer = ProjectAnalyzer(str(ROOT))
    first = analyzer.analyze()
    assert not analyzer._edge_target_in_progress
    budget = analyzer._ownership_proof_budget
    assert budget.depth == 0
    second = analyzer.analyze()
    assert analyzer._ownership_proof_budget is not budget
    assert not analyzer._edge_target_in_progress
    assert [(c.expression, c.top_library) for c in first.all_api_calls] == [
        (c.expression, c.top_library) for c in second.all_api_calls]


def test_deep_source_proof_stays_unknown_and_next_query_is_independent():
    analyzer = ProjectAnalyzer(str(ROOT))
    source = PythonShape('str')
    for _ in range(40):
        source = SourceSet((source,))
    assert analyzer._origin_candidates('main', source, {}) == ['unknown']
    assert analyzer._returned_python_shape('main', source, {}) is None
    assert analyzer._origin_candidates('main', PythonShape('str'), {}) == ['python']
    assert analyzer._returned_python_shape('main', PythonShape('str'), {}) == PythonShape('str')


def test_failed_target_query_does_not_poison_a_later_query(monkeypatch):
    analyzer = ProjectAnalyzer(str(ROOT))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    edge = next(edge for edge in analyzer.project_cg.modules['main'].edges
                if edge.callee_name == 'self._concat')
    original = analyzer._unguarded_edge_targets_local_function

    def fail(*args, **kwargs):
        raise RuntimeError('failed proof')

    monkeypatch.setattr(analyzer, '_unguarded_edge_targets_local_function', fail)
    with pytest.raises(RuntimeError, match='failed proof'):
        analyzer._local_edge_targets(edge, 'main', tracers)
    assert not analyzer._edge_target_in_progress
    assert analyzer._ownership_proof_budget.depth == 0
    monkeypatch.setattr(analyzer, '_unguarded_edge_targets_local_function', original)
    assert [target.qualname for target in analyzer._local_edge_targets(
        edge, 'main', tracers)] == ['Index._concat']


def test_wide_source_proof_does_not_converge_from_truncated_candidates():
    analyzer = ProjectAnalyzer(str(ROOT))
    source = SourceSet((PythonShape('str'),) * 4100)
    assert analyzer._origin_candidates('main', source, {}) == ['unknown']
    assert analyzer._origin_candidates('main', PythonShape('str'), {}) == ['python']


def test_flow_chain_and_recursive_peer_keep_explicit_evidence():
    analyzer = FlowAnalyzer(source_files=[ROOT / 'main.py'], import_roots=[ROOT])
    result = analyzer.analyze(FunctionRef(module='main', qualname='Index.append'),
                              max_depth=3)
    assert result.trace_parameter('other')['return_paths']
    assert result.find_calls(callee_name='self._concat')[0].target.qualname == 'Index._concat'
    assert result.find_calls(callee_name='self._concat_same_dtype')[0].target.qualname == 'Index._concat_same_dtype'
    json.dumps(result.to_dict())
    peer = analyzer.analyze(FunctionRef(module='main', qualname='Index.equals'),
                            max_depth=3)
    assert not peer.trace_parameter('other')['return_paths']
    assert peer.boundaries
