## @package tests.test_ownership_model
#  Tests for the explicit internal ownership run model.

from dataclasses import FrozenInstanceError

import pytest

from pcresolve.cross_file import ProjectAnalyzer
from pcresolve.ownership_model import OwnershipRun, ProgramIndex, ProjectSnapshot
from pcresolve.source_snapshot import OWNERSHIP_SOURCE, SourceStore


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
    with pytest.raises(FrozenInstanceError):
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
