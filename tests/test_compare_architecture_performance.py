## @package tests.test_compare_architecture_performance
#  Performance comparison aggregates every paired sample for a size.

import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile

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


def test_interference_check_uses_external_cpu_fraction_of_pair_duration():
    before = {
        'processes': [{'pid': 20, 'name': 'python.exe', 'cpu_seconds': 4.0,
                       'command_markers': []}],
        'ignored_monitor_pids': [], 'heavy_processes': [],
        'captured_monotonic_seconds': 10.0,
        'cpu_percent': 10.0, 'memory_available_bytes': 4 * 1024 ** 3,
        'memory_available_threshold_bytes': 512 * 1024 ** 2,
    }
    after = dict(before)
    after['captured_monotonic_seconds'] = 20.0
    after['processes'] = [dict(before['processes'][0], cpu_seconds=7.0)]

    result = RUNNER.load_interference(before, after)

    assert result['interference_detected']
    assert result['reasons'] == ['external_process_cpu']
    assert result['external_cpu_processes'][0]['cpu_fraction_of_interval'] == pytest.approx(0.3)


def test_interference_check_detects_aggregate_external_cpu_pressure():
    before = {
        'processes': [dict(pid=pid, name='app.exe', cpu_seconds=1.0,
                           command_markers=[]) for pid in range(5)],
        'ignored_monitor_pids': [], 'heavy_processes': [],
        'captured_monotonic_seconds': 10.0,
        'cpu_percent': 10.0, 'memory_available_bytes': 4 * 1024 ** 3,
        'memory_available_threshold_bytes': 512 * 1024 ** 2,
    }
    after = dict(before)
    after['captured_monotonic_seconds'] = 20.0
    after['processes'] = [dict(process, cpu_seconds=2.6)
                          for process in before['processes']]

    result = RUNNER.load_interference(before, after)

    assert result['interference_detected']
    assert result['reasons'] == ['external_process_cpu']
    assert result['total_external_cpu_fraction_of_interval'] == pytest.approx(0.8)
    assert not any(item['threshold_exceeded']
                   for item in result['external_cpu_processes'])


@pytest.mark.parametrize(
    'interference, candidate_wall, expected_exit, expected_status, attempts',
    [
        ([False, True, False, False], 1.01, 0, 'complete', [1, 2, 1]),
        ([False, True, False, False], 1.30, 1, 'complete', [1, 2, 1]),
        ([False, False, True, True, True], 1.01, 2, 'interference_retries_exhausted',
         [1, 1, 2, 3]),
        ([True], 1.01, 2, 'not_started_due_to_resource_interference', []),
    ],
)
def test_gate_resamples_only_interfered_pairs(
        monkeypatch, tmp_path, interference, candidate_wall, expected_exit, expected_status,
        attempts):
    assessments = iter(interference)
    worker_calls = []
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode='w'):
        pass

    def git_archive(command, **kwargs):
        assert command[:2] == ['git', 'archive']
        return subprocess.CompletedProcess(command, 0, stdout=archive.getvalue())

    def assess(before, after):
        return dict(interference_detected=next(assessments))

    def run_worker(script, output, sizes, repeats, samples):
        assert sizes == [10]
        assert samples == 1
        label = 'after' if script == RUNNER.ROOT / 'scripts' / 'perf_scalability.py' else 'before'
        worker_calls.append(label)
        wall = candidate_wall if label == 'after' else 1.0
        return dict(samples=[dict(
            modules=11, outputs_equal=True,
            runs=[dict(peak_rss_bytes=100, rows=[dict(variant='flow_cold', wall=wall)])],
            worker_call=len(worker_calls))])

    monkeypatch.setattr(RUNNER, 'capture_system_state', dict)
    monkeypatch.setattr(RUNNER, 'load_interference', assess)
    monkeypatch.setattr(RUNNER, 'run_benchmark', run_worker)
    monkeypatch.setattr(RUNNER.subprocess, 'run', git_archive)
    monkeypatch.setattr(sys, 'argv', [str(SCRIPT), '--sizes', '10', '--repeats', '1',
                                      '--independent-samples', '2',
                                      '--interference-retries', '2',
                                      '--output-dir', str(tmp_path)])

    assert RUNNER.main() == expected_exit

    environment = json.loads((tmp_path / 'performance-environment.json').read_text())
    comparison = json.loads((tmp_path / 'performance-comparison.json').read_text())
    snapshots = environment['snapshots']
    accepted = [not rejected for rejected in interference[1:]]
    assert environment['status'] == comparison['environment_status'] == expected_status
    assert [entry['attempt'] for entry in snapshots] == attempts
    assert [entry['accepted'] for entry in snapshots] == accepted
    assert comparison['environment_valid'] == (expected_exit != 2)
    assert comparison['passed'] == (expected_exit == 0)
    assert bool(comparison['comparisons']) == (expected_exit != 2)
    if expected_exit == 1:
        assert [row['metric'] for row in comparison['comparisons']
                if not row['passed']] == ['wall_seconds']
    discarded = [entry['discarded_samples'] for entry in snapshots if not entry['accepted']]
    for label in ('before', 'after'):
        report = json.loads((tmp_path / ('performance-%s.json' % label)).read_text())
        assert report['samples_completed'] == len(report['samples']) == sum(accepted)
        assert {sample['worker_call'] for sample in report['samples']}.isdisjoint(
            pair[label]['worker_call'] for pair in discarded)
    if expected_status == 'complete':
        assert worker_calls == ['before', 'after', 'before', 'after', 'after', 'before']
