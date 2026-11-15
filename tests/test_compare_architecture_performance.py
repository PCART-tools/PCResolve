## @package tests.test_compare_architecture_performance
#  Performance comparison aggregates every paired sample for a size.

import importlib.util
from pathlib import Path

import pytest


SCRIPT = (Path(__file__).parents[1] / 'scripts' /
         'compare_architecture_performance.py')
SPEC = importlib.util.spec_from_file_location('architecture_performance', SCRIPT)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_medians_aggregates_paired_samples_for_same_size():
    report = {'samples': [
        {'modules': 101, 'outputs_equal': True, 'runs': [
            {'peak_rss_bytes': 100, 'rows': [
                {'variant': 'flow_cold', 'wall': 1.0}] }]},
        {'modules': 101, 'outputs_equal': True, 'runs': [
            {'peak_rss_bytes': 200, 'rows': [
                {'variant': 'flow_cold', 'wall': 3.0}] }]},
    ]}

    result = RUNNER.medians(report)[101]

    assert result == {
        'wall': {'flow_cold': 2.0},
        'peak_rss_bytes': 150,
        'outputs_equal': True,
    }


def test_paired_delta_uses_each_baseline_candidate_sample_pair():
    before = [0.404, 0.223, 0.230, 0.247, 0.326]
    after = [0.384, 0.260, 0.330, 0.328, 0.251]
    delta, samples = RUNNER.paired_median_delta(
        before, after)

    assert samples == pytest.approx([-0.020, 0.037, 0.100, 0.081, -0.075])
    assert delta == pytest.approx(0.037)
    assert delta <= 0.050  # Diagnostic only; the aggregate gate still fails.
    assert not RUNNER.within_regression_allowance(
        0.247, 0.328, 0.050)


def test_benchmark_worker_drops_inherited_python_paths(monkeypatch, tmp_path):
    captured = {}

    def run(command, capture_output, text, env):
        captured.update(env)
        output = Path(command[command.index('--output') + 1])
        output.write_text('{"samples": []}', encoding='utf-8')
        return type('Completed', (), {'returncode': 0})()

    monkeypatch.setenv('PYTHONPATH', 'foreign-checkout')
    monkeypatch.setenv('PYTHONHOME', 'foreign-runtime')
    monkeypatch.setenv('VIRTUAL_ENV', 'foreign-venv')
    monkeypatch.setattr(RUNNER.subprocess, 'run', run)

    RUNNER.run_benchmark(SCRIPT, tmp_path / 'worker.json', [10], 1, 1)

    assert not {'PYTHONPATH', 'PYTHONHOME', 'VIRTUAL_ENV'} & captured.keys()
    assert captured['PYTHONHASHSEED'] == '0'
    assert captured['PYTHONNOUSERSITE'] == '1'


def test_interference_check_ignores_measurement_process_ancestors():
    before = {
        'processes': [{'pid': 10, 'name': 'python', 'cpu_seconds': 1.0,
                       'command_markers': ['run_ci_gate.py']}],
        'ignored_monitor_pids': [10], 'heavy_processes': [],
        'cpu_percent': 2.0, 'memory_available_bytes': 4 * 1024 ** 3,
        'memory_available_threshold_bytes': 512 * 1024 ** 2,
    }
    after = dict(before)
    after['processes'] = [dict(before['processes'][0], cpu_seconds=8.0)]

    result = RUNNER.load_interference(before, after)

    assert not result['interference_detected']
    assert result['external_cpu_processes'] == []
