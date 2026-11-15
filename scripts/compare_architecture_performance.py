#!/usr/bin/env python3
## @package scripts.compare_architecture_performance
#  Run the same isolated-process workloads against a source revision and checkout.

import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile

import psutil

ROOT = Path(__file__).resolve().parents[1]
_HEAVY_COMMAND_MARKERS = (
    'pytest', 'mypy', 'compare_analysis_baseline.py', 'evaluate_ground_truth.py',
    'verify_release_artifacts.py', 'perf_scalability.py', 'run_ci_gate.py',
)
_MIN_AVAILABLE_MEMORY = 512 * 1024 * 1024
_MIN_AVAILABLE_MEMORY_RATIO = 0.05
_HIGH_CPU_PERCENT = 90.0
_HIGH_EXTERNAL_PROCESS_CPU_SECONDS = 1.0


def capture_system_state():
    """Capture host load and active Python processes for benchmark provenance."""
    cpu_percent = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    ignored_pids = {os.getpid()}
    try:
        ignored_pids.update(parent.pid for parent in psutil.Process().parents())
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        pass
    processes = []
    for process in psutil.process_iter(
            attrs=('pid', 'name', 'cmdline', 'cpu_times', 'memory_info')):
        try:
            info = process.info
            command = ' '.join(info.get('cmdline') or ())
            if not command:
                continue
            name = info.get('name') or ''
            markers = [marker for marker in _HEAVY_COMMAND_MARKERS
                       if marker in command.lower()]
            cpu = info.get('cpu_times')
            memory_info = info.get('memory_info')
            processes.append(dict(
                pid=info['pid'], name=name,
                command_markers=markers,
                cpu_seconds=(cpu.user + cpu.system) if cpu else 0.0,
                rss_bytes=memory_info.rss if memory_info else 0))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    heavy = [process for process in processes
             if process['pid'] not in ignored_pids and process['command_markers']]
    minimum_memory = max(_MIN_AVAILABLE_MEMORY,
                         int(memory.total * _MIN_AVAILABLE_MEMORY_RATIO))
    return dict(cpu_percent=cpu_percent, memory_total_bytes=memory.total,
                memory_available_bytes=memory.available,
                memory_available_threshold_bytes=minimum_memory,
                ignored_monitor_pids=sorted(ignored_pids),
                heavy_processes=heavy, processes=processes)


def load_interference(before, after):
    """Identify heavy concurrent work or high resource pressure between snapshots."""
    before_by_pid = {item['pid']: item for item in before['processes']}
    ignored_pids = set(before.get('ignored_monitor_pids', ())) | set(
        after.get('ignored_monitor_pids', ()))
    external_cpu = []
    for process in after['processes']:
        if process['pid'] in ignored_pids:
            continue
        previous = before_by_pid.get(process['pid'])
        if previous is None:
            continue
        delta = process['cpu_seconds'] - previous['cpu_seconds']
        if delta >= _HIGH_EXTERNAL_PROCESS_CPU_SECONDS:
            external_cpu.append(dict(pid=process['pid'], name=process['name'],
                                     command_markers=process['command_markers'],
                                     cpu_seconds_delta=delta))
    reasons = []
    if before['heavy_processes'] or after['heavy_processes']:
        reasons.append('concurrent_heavy_process')
    if max(before['cpu_percent'], after['cpu_percent']) >= _HIGH_CPU_PERCENT:
        reasons.append('high_system_cpu')
    if min(before['memory_available_bytes'], after['memory_available_bytes']) < max(
            before['memory_available_threshold_bytes'],
            after['memory_available_threshold_bytes']):
        reasons.append('low_available_memory')
    if external_cpu:
        reasons.append('external_process_cpu')
    return dict(interference_detected=bool(reasons), reasons=reasons,
                external_cpu_processes=external_cpu)


def run_benchmark(script, output, sizes, repeats, samples):
    command = [sys.executable, str(script), '--sizes'] + [str(size) for size in sizes]
    command += ['--repeats', str(repeats), '--independent-samples', str(samples),
                '--output', str(output)]
    environment = dict(os.environ)
    for name in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONUSERBASE', 'VIRTUAL_ENV'):
        environment.pop(name, None)
    environment['PYTHONHASHSEED'] = '0'
    environment['PYTHONNOUSERSITE'] = '1'
    result = subprocess.run(command, capture_output=True, text=True, env=environment)
    if result.returncode:
        raise RuntimeError('benchmark failed (%s):\n%s\n%s' %
                           (script, result.stdout[-4000:], result.stderr[-4000:]))
    return json.loads(output.read_text(encoding='utf-8'))


def run_paired_benchmarks(before_script, after_script, output_dir,
                          sizes, repeats, samples):
    """Measure baseline and candidate in alternating, paired worker runs."""
    before_report = dict(samples=[])
    after_report = dict(samples=[])
    before_report_path = output_dir / 'performance-before.json'
    after_report_path = output_dir / 'performance-after.json'
    environment_report = dict(
        sampling_strategy='alternating paired isolated-process samples',
        ignored_processes='monitor process and its parent process chain',
        interference_thresholds=dict(
            heavy_process_markers=list(_HEAVY_COMMAND_MARKERS),
            high_cpu_percent=_HIGH_CPU_PERCENT,
            external_process_cpu_seconds=_HIGH_EXTERNAL_PROCESS_CPU_SECONDS,
            minimum_available_memory_bytes=_MIN_AVAILABLE_MEMORY,
            minimum_available_memory_ratio=_MIN_AVAILABLE_MEMORY_RATIO),
        snapshots=[])
    initial_state = capture_system_state()
    initial_assessment = load_interference(initial_state, initial_state)
    environment_report['initial_state'] = initial_state
    environment_report['initial_assessment'] = initial_assessment
    environment_report['environment_valid'] = not initial_assessment['interference_detected']
    environment_path = output_dir / 'performance-environment.json'
    if not environment_report['environment_valid']:
        environment_report['status'] = 'not_started_due_to_resource_interference'
        environment_path.write_text(json.dumps(environment_report, indent=2),
                                    encoding='utf-8')
        return None, None, environment_report
    environment_report['status'] = 'running'
    environment_path.write_text(json.dumps(environment_report, indent=2), encoding='utf-8')
    with tempfile.TemporaryDirectory(prefix='pcresolve-perf-pairs-') as temp:
        sample_dir = Path(temp)
        for size in sizes:
            for sample_index in range(samples):
                pair_before = capture_system_state()
                order = (('before', before_script), ('after', after_script))
                if sample_index % 2:
                    order = tuple(reversed(order))
                for label, script in order:
                    output = sample_dir / ('%s-%s-%s.json' %
                                           (label, size, sample_index))
                    result = run_benchmark(script, output, [size], repeats, 1)
                    report = before_report if label == 'before' else after_report
                    if 'python' not in report:
                        report.update({key: result[key] for key in
                                       ('python', 'platform', 'analyzer_sha256',
                                        'repeats', 'independent_samples')
                                       if key in result})
                    sample = result['samples'][0]
                    report['samples'].append(sample)
                # Keep complete partial evidence if a later worker fails.
                completed = len(before_report['samples'])
                for report in (before_report, after_report):
                    report['independent_samples'] = samples
                    report['samples_completed'] = completed
                before_report_path.write_text(
                    json.dumps(before_report, indent=2), encoding='utf-8')
                after_report_path.write_text(
                    json.dumps(after_report, indent=2), encoding='utf-8')
                pair_after = capture_system_state()
                assessment = load_interference(pair_before, pair_after)
                environment_report['snapshots'].append(dict(
                    modules=size + 1, sample=sample_index,
                    before=pair_before, after=pair_after, assessment=assessment))
                if assessment['interference_detected']:
                    environment_report['environment_valid'] = False
                environment_report['status'] = (
                    'complete' if environment_report['environment_valid'] else
                    'complete_but_interfered')
                environment_path.write_text(json.dumps(environment_report, indent=2),
                                            encoding='utf-8')
    return before_report, after_report, environment_report


def medians(report):
    grouped = {}
    for sample in report['samples']:
        data = grouped.setdefault(sample['modules'],
                                  dict(wall={}, peak_rss_bytes=[], outputs_equal=[]))
        data['outputs_equal'].append(sample['outputs_equal'])
        for run in sample['runs']:
            data['peak_rss_bytes'].append(run['peak_rss_bytes'])
            for row in run['rows']:
                data['wall'].setdefault(row['variant'], []).append(row['wall'])
    return {
        modules: dict(
            wall={key: statistics.median(values)
                  for key, values in data['wall'].items()},
            peak_rss_bytes=statistics.median(data['peak_rss_bytes']),
            outputs_equal=all(data['outputs_equal']))
        for modules, data in grouped.items()
    }


def paired_median_delta(before_values, after_values):
    """Return the median candidate-minus-baseline delta for paired samples."""
    if len(before_values) != len(after_values):
        raise ValueError('Baseline and candidate sample counts must match')
    deltas = [after - before for before, after in zip(before_values, after_values)]
    return statistics.median(deltas), deltas


def within_regression_allowance(before_median, after_median, allowance):
    """Apply the release gate to aggregate baseline and candidate medians."""
    return after_median <= before_median + allowance


def sample_medians(report):
    """Return per-worker medians, preserving independent sample pairing."""
    result = {}
    for sample in report['samples']:
        values = {}
        peaks = []
        for run in sample['runs']:
            peaks.append(run['peak_rss_bytes'])
            for row in run['rows']:
                values.setdefault(row['variant'], []).append(row['wall'])
        result.setdefault(sample['modules'], []).append(dict(
            wall={key: statistics.median(rows) for key, rows in values.items()},
            peak_rss_bytes=statistics.median(peaks),
            outputs_equal=sample['outputs_equal']))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-ref', default='HEAD')
    parser.add_argument('--sizes', type=int, nargs='+', default=[10, 100, 500])
    parser.add_argument('--repeats', type=int, default=5)
    parser.add_argument('--independent-samples', type=int, default=5)
    parser.add_argument('--output-dir', type=Path,
                        default=Path('reports/architecture-1.0.8'))
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    before_path = output_dir / 'performance-before.json'
    after_path = output_dir / 'performance-after.json'
    with tempfile.TemporaryDirectory(prefix='pcresolve-perf-baseline-') as directory:
        archive = subprocess.run(['git', 'archive', '--format=tar', args.baseline_ref],
                                 cwd=ROOT, check=True, capture_output=True).stdout
        with tarfile.open(fileobj=__import__('io').BytesIO(archive), mode='r:') as bundle:
            if sys.version_info >= (3, 12):
                bundle.extractall(directory, filter='data')
            else:
                bundle.extractall(directory)
        baseline_root = Path(directory)
        baseline_script = baseline_root / 'scripts' / 'perf_scalability.py'
        baseline_script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'scripts' / 'perf_scalability.py', baseline_script)
        before, after, environment_report = run_paired_benchmarks(
            baseline_script, ROOT / 'scripts' / 'perf_scalability.py',
            output_dir, args.sizes, args.repeats, args.independent_samples)
    if before is None or after is None:
        print('performance measurement not started: resource interference detected')
        return 2
    old, new = medians(before), medians(after)
    old_samples, new_samples = sample_medians(before), sample_medians(after)
    comparisons = []
    for size in args.sizes:
        modules = size + 1
        old_row, new_row = old[modules], new[modules]
        for variant, old_seconds in old_row['wall'].items():
            new_seconds = new_row['wall'][variant]
            allowance = max(old_seconds * 0.10, 0.050)
            paired_delta, paired_deltas = paired_median_delta(
                [sample['wall'][variant] for sample in old_samples[modules]],
                [sample['wall'][variant] for sample in new_samples[modules]])
            comparisons.append(dict(modules=modules, metric='wall_seconds', variant=variant,
                                    before=old_seconds, after=new_seconds,
                                    allowance=allowance,
                                    paired_delta_median=paired_delta,
                                    paired_deltas=paired_deltas,
                                    passed=within_regression_allowance(
                                        old_seconds, new_seconds, allowance)))
        old_peak, new_peak = old_row['peak_rss_bytes'], new_row['peak_rss_bytes']
        allowance = max(old_peak * 0.10, 10 * 1024 * 1024)
        paired_delta, paired_deltas = paired_median_delta(
            [sample['peak_rss_bytes'] for sample in old_samples[modules]],
            [sample['peak_rss_bytes'] for sample in new_samples[modules]])
        comparisons.append(dict(modules=modules, metric='peak_rss_bytes',
                                before=old_peak, after=new_peak, allowance=allowance,
                                paired_delta_median=paired_delta,
                                paired_deltas=paired_deltas,
                                passed=within_regression_allowance(
                                    old_peak, new_peak, allowance)))
        comparisons.append(dict(modules=modules, metric='output_reuse_equivalence',
                                before=old_row['outputs_equal'], after=new_row['outputs_equal'],
                                passed=old_row['outputs_equal'] and new_row['outputs_equal']))
    report = dict(baseline_ref=args.baseline_ref, python=sys.version,
                  sizes=args.sizes, repeats=args.repeats,
                  independent_samples=args.independent_samples,
                  sampling_strategy='alternating paired isolated-process samples',
                  regression_rule='candidate median <= baseline median + original allowance',
                  environment_valid=environment_report['environment_valid'],
                  environment_report=str(output_dir / 'performance-environment.json'),
                  benchmark_environment=dict(hash_seed='0',
                                             removed_inherited_python_path=True,
                                             user_site_disabled=True),
                  before=str(before_path), after=str(after_path),
                  passed=(environment_report['environment_valid']
                          and all(row['passed'] for row in comparisons)),
                  comparisons=comparisons)
    comparison_path = output_dir / 'performance-comparison.json'
    comparison_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('performance thresholds passed: %s; comparisons=%d' %
          (report['passed'], len(comparisons)))
    if not environment_report['environment_valid']:
        print('results are diagnostic only: concurrent resource interference detected')
        return 2
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
