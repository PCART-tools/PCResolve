#!/usr/bin/env python3
## @package scripts.compare_architecture_performance
#  Run the same isolated-process workloads against a source revision and checkout.

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import statistics

ROOT = Path(__file__).resolve().parents[1]


def run_benchmark(script, output, sizes, repeats, samples):
    command = [sys.executable, str(script), '--sizes'] + [str(size) for size in sizes]
    command += ['--repeats', str(repeats), '--independent-samples', str(samples),
                '--output', str(output)]
    environment = dict(os.environ, PYTHONHASHSEED='0')
    result = subprocess.run(command, capture_output=True, text=True, env=environment)
    if result.returncode:
        raise RuntimeError('benchmark failed (%s):\n%s\n%s' %
                           (script, result.stdout[-4000:], result.stderr[-4000:]))
    return json.loads(output.read_text(encoding='utf-8'))


def medians(report):
    by_size = {}
    for sample in report['samples']:
        times = {}
        peaks = []
        for run in sample['runs']:
            peaks.append(run['peak_rss_bytes'])
            for row in run['rows']:
                times.setdefault(row['variant'], []).append(row['wall'])
        by_size[sample['modules']] = dict(
            wall={key: statistics.median(values) for key, values in times.items()},
            peak_rss_bytes=statistics.median(peaks),
            outputs_equal=sample['outputs_equal'])
    return by_size


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
    after = run_benchmark(ROOT / 'scripts' / 'perf_scalability.py', after_path,
                          args.sizes, args.repeats, args.independent_samples)
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
        before = run_benchmark(baseline_script, before_path, args.sizes,
                               args.repeats, args.independent_samples)
    old, new = medians(before), medians(after)
    comparisons = []
    for size in args.sizes:
        modules = size + 1
        old_row, new_row = old[modules], new[modules]
        for variant, old_seconds in old_row['wall'].items():
            new_seconds = new_row['wall'][variant]
            allowance = max(old_seconds * 0.10, 0.050)
            comparisons.append(dict(modules=modules, metric='wall_seconds', variant=variant,
                                    before=old_seconds, after=new_seconds,
                                    allowance=allowance,
                                    passed=new_seconds <= old_seconds + allowance))
        old_peak, new_peak = old_row['peak_rss_bytes'], new_row['peak_rss_bytes']
        allowance = max(old_peak * 0.10, 10 * 1024 * 1024)
        comparisons.append(dict(modules=modules, metric='peak_rss_bytes',
                                before=old_peak, after=new_peak, allowance=allowance,
                                passed=new_peak <= old_peak + allowance))
        comparisons.append(dict(modules=modules, metric='output_reuse_equivalence',
                                before=old_row['outputs_equal'], after=new_row['outputs_equal'],
                                passed=old_row['outputs_equal'] and new_row['outputs_equal']))
    report = dict(baseline_ref=args.baseline_ref, python=sys.version,
                  sizes=args.sizes, repeats=args.repeats,
                  independent_samples=args.independent_samples,
                  before=str(before_path), after=str(after_path),
                  passed=all(row['passed'] for row in comparisons), comparisons=comparisons)
    comparison_path = output_dir / 'performance-comparison.json'
    comparison_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('performance thresholds passed: %s; comparisons=%d' %
          (report['passed'], len(comparisons)))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
