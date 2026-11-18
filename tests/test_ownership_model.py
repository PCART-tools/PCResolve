## @package tests.test_ownership_model
#  Tests for the explicit internal ownership run model.


import pytest

from pcresolve.ownership.analyzer import ProjectAnalyzer
from pcresolve.ownership.ownership_model import OwnershipRun, ProgramIndex, ProjectSnapshot
from pcresolve.ownership.call_graph import ProjectCallGraph
from pcresolve.frontend.source_snapshot import OWNERSHIP_SOURCE, SourceStore
from pcresolve.runtime.limits import AnalysisLimitExceeded, AnalysisLimits
from pcresolve.ownership.views import build_full_view


def test_ownership_run_models_keep_snapshot_fixed_and_mutable_state_isolated(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('print("ok")\n', encoding='utf-8')
    sources = SourceStore().snapshot([str(path)], OWNERSHIP_SOURCE)
    snapshot = ProjectSnapshot(('main',), sources)

    first = OwnershipRun(snapshot)
    second = OwnershipRun(snapshot)

    assert first.snapshot.modules == ('main',)
    assert first.snapshot.sources is sources
    assert isinstance(first.program, ProgramIndex)
    assert first.program is not second.program
    assert first.diagnostics is not second.diagnostics
    with pytest.raises(AttributeError):
        snapshot.modules = ()


def test_project_analyzer_builds_and_uses_one_explicit_ownership_run(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('import json\nvalue = json.loads("{}")\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))

    result = analyzer.analyze()
    run = analyzer._ownership_run

    assert run.snapshot.modules == ('main',)
    assert run.snapshot.sources is analyzer._source_snapshot
    assert tuple(run.program.module_tracers) == ('main',)
    assert run.program.module_tracers['main'].module_name == 'main'
    assert run.program.call_graph is analyzer.project_cg
    assert run.program.call_graph.modules['main'] is run.program.module_tracers['main'].module_cg
    assert run.diagnostics is result.diagnostics
    assert [call.top_library for call in result.all_api_calls] == ['json']


def test_each_analysis_replaces_project_tables_and_resolution_guards(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('import json\nvalue = json.loads("{}")\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    first = analyzer._ownership_run

    first.global_symbols['stale'] = 'value'
    first.symbol_chains['stale'] = ['value']
    first.all_calls['stale'] = []
    first.python_shape_in_progress.add(('main', 'stale'))
    first.callable_field_in_progress.add(('main', 'stale'))
    first.constructor_only_fields = {'stale'}

    analyzer.analyze()
    second = analyzer._ownership_run

    assert second is not first
    assert analyzer.global_symbols is second.global_symbols
    assert analyzer.symbol_chains is second.symbol_chains
    assert analyzer.all_calls is second.all_calls
    assert analyzer._python_shape_in_progress is second.python_shape_in_progress
    assert analyzer._callable_field_in_progress is second.callable_field_in_progress
    assert 'stale' not in second.global_symbols
    assert 'stale' not in second.symbol_chains
    assert 'stale' not in second.all_calls
    assert not second.python_shape_in_progress
    assert not second.callable_field_in_progress
    assert second.constructor_only_fields is None


def test_constructor_evidence_compatibility_view_uses_active_run(tmp_path):
    (tmp_path / 'main.py').write_text('value = 1\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer._constructor_only_fields = {'before'}
    assert analyzer._constructor_only_fields == {'before'}

    analyzer.analyze()
    first = analyzer._ownership_run
    assert analyzer._constructor_only_fields is None
    first.constructor_only_fields = {'from_run'}
    assert analyzer._constructor_only_fields == {'from_run'}
    analyzer._constructor_only_fields = {'from_alias'}
    assert first.constructor_only_fields == {'from_alias'}
    analyzer.analyze()
    assert analyzer._ownership_run is not first
    assert analyzer._constructor_only_fields is None
    assert first.constructor_only_fields == {'from_alias'}


@pytest.mark.parametrize('name', ['global_symbols', 'symbol_chains', 'all_calls'])
def test_project_tables_compatibility_view_tracks_replacement_and_run(tmp_path, name):
    (tmp_path / 'main.py').write_text('print(1)\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    before = {'before': 1}
    setattr(analyzer, name, before)
    assert getattr(analyzer, name) is before
    analyzer.analyze()
    first = analyzer._ownership_run
    assert '_initial_' + name not in analyzer.__dict__
    assert getattr(analyzer, name) is getattr(first, name)
    via_run = {'run': 1}
    setattr(first, name, via_run)
    assert getattr(analyzer, name) is via_run
    via_alias = {'alias': 1}
    setattr(analyzer, name, via_alias)
    assert getattr(first, name) is via_alias
    analyzer.analyze()
    assert getattr(analyzer, name) is getattr(analyzer._ownership_run, name)
    assert getattr(analyzer, name) is not via_alias
    assert getattr(first, name) is via_alias


@pytest.mark.parametrize(('alias', 'field'), [
    ('_python_shape_in_progress', 'python_shape_in_progress'),
    ('_callable_field_in_progress', 'callable_field_in_progress'),
    ('_edge_target_in_progress', 'edge_target_in_progress'),
    ('_ownership_proof_budget', 'proof_budget'),
])
def test_run_guard_and_budget_compatibility_views_track_replacement(tmp_path, alias, field):
    (tmp_path / 'main.py').write_text('print(1)\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    initial = getattr(analyzer, alias)
    analyzer.analyze()
    first = analyzer._ownership_run
    assert getattr(analyzer, alias) is getattr(first, field)
    assert getattr(analyzer, alias) is not initial
    replacement = object()
    setattr(first, field, replacement)
    assert getattr(analyzer, alias) is replacement
    replacement2 = object()
    setattr(analyzer, alias, replacement2)
    assert getattr(first, field) is replacement2
    analyzer.analyze()
    assert getattr(analyzer, alias) is getattr(analyzer._ownership_run, field)
    assert getattr(analyzer, alias) is not replacement2


@pytest.mark.parametrize(('guard', 'method', 'inner', 'arguments'), [
    ('python_shape_in_progress', '_returned_python_shape', '_infer_returned_python_shape',
     ('main', 'source', {})),
    ('edge_target_in_progress', '_edge_targets_local_function',
     '_unguarded_edge_targets_local_function', (object(), 'main', 'target', 'f', None, {})),
])
def test_active_run_guards_and_proof_depth_restore_after_failure(
        tmp_path, monkeypatch, guard, method, inner, arguments):
    (tmp_path / 'main.py').write_text('print(1)\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    run = analyzer._ownership_run
    def fail(*args, **kwargs):
        assert getattr(run, guard)
        assert run.proof_budget.depth == 1
        raise RuntimeError('injected resolver failure')
    with monkeypatch.context() as patch:
        patch.setattr(analyzer, inner, fail)
        with pytest.raises(RuntimeError, match='injected resolver failure'):
            getattr(analyzer, method)(*arguments)
    assert not getattr(run, guard)
    assert run.proof_budget.depth == 0
    monkeypatch.setattr(analyzer, inner, lambda *args, **kwargs: True)
    assert getattr(analyzer, method)(*arguments) is True
    assert not getattr(run, guard)
    assert run.proof_budget.depth == 0


def test_snapshot_and_call_graph_are_views_of_active_run(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('print(1)\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    assert not hasattr(analyzer, '_source_snapshot')
    assert not hasattr(analyzer, 'project_cg')
    initial = ProjectCallGraph()
    analyzer.project_cg = initial
    assert analyzer.project_cg is initial
    analyzer.analyze()
    first = analyzer._ownership_run
    assert analyzer._source_snapshot is first.snapshot.sources
    assert analyzer.project_cg is first.program.call_graph
    replacement = ProjectCallGraph()
    analyzer.project_cg = replacement
    assert first.program.call_graph is replacement
    another = ProjectCallGraph()
    first.program.call_graph = another
    assert analyzer.project_cg is another
    path.write_text('print(2)\n', encoding='utf-8')
    analyzer.analyze()
    second = analyzer._ownership_run
    assert analyzer._source_snapshot is second.snapshot.sources
    assert second.snapshot.sources is not first.snapshot.sources
    assert analyzer.project_cg is second.program.call_graph
    assert analyzer.project_cg is not another


def test_analysis_budget_is_owned_by_the_active_run(tmp_path):
    (tmp_path / 'main.py').write_text('value = 1\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), analysis_limits=AnalysisLimits(max_work=1000))

    analyzer.analyze()

    run = analyzer._ownership_run
    assert run.analysis_budget is analyzer._analysis_budget
    assert run.ast_facts.budget is run.analysis_budget


def test_budget_failure_before_run_creation_keeps_previous_run_and_retry_is_fresh(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('import json\njson.loads("{}")\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    analyzer.analyze()
    previous = analyzer._ownership_run
    previous.global_symbols['sentinel'] = 'old run only'
    previous_cache = analyzer._source_fact_cache
    path.write_text('import json\njson.dumps({})\n', encoding='utf-8')
    analyzer.analysis_limits = AnalysisLimits(max_work=1)
    with pytest.raises(AnalysisLimitExceeded, match='work'):
        analyzer.analyze()
    assert analyzer._ownership_run is previous
    assert analyzer._analysis_budget is previous.analysis_budget
    assert analyzer._source_fact_cache is previous_cache
    analyzer.analysis_limits = None
    actual = build_full_view(analyzer.analyze())
    assert analyzer._ownership_run is not previous
    assert 'sentinel' not in analyzer._ownership_run.global_symbols
    assert actual == build_full_view(ProjectAnalyzer(str(tmp_path)).analyze())
