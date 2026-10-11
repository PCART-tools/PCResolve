## @package tests.test_analysis_limits
#  Explicit whole-analysis limits stop work without manufacturing ownership.

import pytest

from pcresolve import FlowAnalyzer, FunctionRef, ProjectAnalyzer
from pcresolve.analysis_limits import AnalysisLimits, AnalysisBudget, AnalysisLimitExceeded
from pcresolve.cli import main
import sys


def test_budget_checks_total_work_and_resets_between_analyses(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('def entry(value): return value\nprint(entry(1))\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), analysis_limits=AnalysisLimits(max_work=1))
    with pytest.raises(AnalysisLimitExceeded, match='work'):
        analyzer.analyze()
    analyzer.analysis_limits = AnalysisLimits(max_work=10000)
    assert analyzer.analyze().all_api_calls
    assert analyzer.analyze().all_api_calls


def test_flow_limits_include_source_indexing_and_query_work(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('def entry(value): return value\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path, analysis_limits=AnalysisLimits(max_work=1))
    with pytest.raises(AnalysisLimitExceeded):
        analyzer.analyze(FunctionRef(module='main', qualname='entry'))
    analyzer.analysis_limits = None
    assert analyzer.analyze(FunctionRef(module='main', qualname='entry')).functions


def test_deadline_and_memory_checks_are_deterministic():
    clock = iter((0.0, 2.0))
    budget = AnalysisBudget(AnalysisLimits(max_seconds=1), clock=lambda: next(clock))
    with pytest.raises(AnalysisLimitExceeded, match='time'):
        budget.checkpoint(force=True)
    budget = AnalysisBudget(AnalysisLimits(max_memory_mb=1), memory=lambda: 2 * 1024 * 1024)
    with pytest.raises(AnalysisLimitExceeded, match='memory'):
        budget.checkpoint(force=True)


def test_flow_checks_limits_before_returning_completed_output(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text('def entry(value): return value\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path,
                            analysis_limits=AnalysisLimits(max_memory_mb=1))
    import pcresolve.flow as flow_module
    usage = [0]
    monkeypatch.setattr(flow_module, 'AnalysisBudget', lambda limits: AnalysisBudget(
        limits, memory=lambda: usage[0]))
    original = analyzer._walk
    def finish(*args, **kwargs):
        original(*args, **kwargs)
        usage[0] = 2 * 1024 * 1024
    monkeypatch.setattr(analyzer, '_walk', finish)
    with pytest.raises(AnalysisLimitExceeded, match='memory'):
        analyzer.analyze(FunctionRef(module='main', qualname='entry'))


@pytest.mark.parametrize('limits', [dict(max_work=0), dict(max_seconds=-1),
                                   dict(max_memory_mb=0), dict(max_seconds=float('nan'))])
def test_limits_reject_invalid_values(limits):
    with pytest.raises(ValueError):
        AnalysisLimits(**limits)


@pytest.mark.parametrize('flow', [False, True])
def test_cli_reports_resource_boundary_without_result_json(tmp_path, monkeypatch, capsys, flow):
    path = tmp_path / 'main.py'
    path.write_text('def entry(value): return value\nprint(entry(1))\n', encoding='utf-8')
    args = ['pcresolve', str(path), '--max-work', '1', '--json']
    if flow:
        args.extend(['--value-flow', '--entry', 'main:entry'])
    monkeypatch.setattr(sys, 'argv', args)
    with pytest.raises(SystemExit) as error:
        main()
    output = capsys.readouterr()
    assert error.value.code != 0
    assert output.out == ''
    assert 'work limit exceeded' in output.err
