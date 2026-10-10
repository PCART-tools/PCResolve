## @package reports.performance_audit.run_matrix
#  Serial fresh-process audit driver. Saves partial progress and enforces wall limits.
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ['TEMP']) / 'pcresolve-pandas-batch-repro'
OUT = Path(os.environ['TEMP']) / 'pcresolve-performance-audit'


## Run serial measurements with output and timeout records.
#  @return None.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('group', choices=['batches', 'ablation', 'controlled', 'profiles', 'scope', 'small-probes'])
    args = parser.parse_args()
    groups = {}
    batches = sorted(DATA.glob('step2-*/pandas'))
    groups['batches'] = [(p.parent.name, p, [], 240) for p in batches]
    selected = [p for p in batches if p.parent.name.startswith(('step2-2-normal-', 'step2-2-timeout-', 'step2-2-longest-', 'step2-3-longest-'))]
    groups['ablation'] = [(p.parent.name + '-' + variant, p, ['--variant', variant, '--repeat', '2'], 480)
                          for p in selected for variant in ('baseline', 'empty-arguments')]
    groups['controlled'] = groups['ablation']
    groups['profiles'] = [(p.parent.name, p, ['--profile', '--proofs'], 480)
                          for p in selected if p.parent.name.startswith(('step2-2-timeout-', 'step2-2-longest-'))]
    groups['scope'] = [('base-single', DATA / 'pandas-0.21.0/pandas/core/indexes/base.py', [], 180),
                       ('allnews', ROOT / 'tests/fixtures/tested_projects/allnews', [], 180),
                       ('pandas-full', DATA / 'pandas-0.21.0' / 'pandas', [], 180),
                       ('pcresolve-self', ROOT / 'src' / 'pcresolve', [], 180)]
    normal = next(p for p in batches if p.parent.name.startswith('step2-2-normal-'))
    groups['small-probes'] = [('normal-seed-' + str(seed), normal, ['--profile', '--proofs'], 90)
                              for seed in (0, 1, 42)]
    groups['small-probes'].append(('normal-gc', normal, ['--gc-stats', '--repeat', '3'], 90))
    jobs = groups.get(args.group, [])
    manifest = []
    parent = OUT / args.group
    parent.mkdir(parents=True, exist_ok=True)
    for name, source, extra, timeout in jobs:
        target = parent / name
        target.mkdir(parents=True, exist_ok=True)
        command = [sys.executable, str(ROOT / 'reports/performance-audit/ownership_probe.py'),
                   str(source), '--out', str(target)] + extra
        print(json.dumps({'start': name, 'timeout': timeout}), flush=True)
        start = time.perf_counter()
        with (target / 'stdout.log').open('w', encoding='utf-8') as stdout, (target / 'stderr.log').open('w', encoding='utf-8') as stderr:
            try:
                seed = name.rsplit('-', 1)[-1] if name.startswith('normal-seed-') else '0'
                process = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=timeout,
                                         env={**os.environ, 'PYTHONHASHSEED': seed})
                record = {'name': name, 'status': 'ok' if process.returncode == 0 else 'error', 'returncode': process.returncode}
            except subprocess.TimeoutExpired:
                record = {'name': name, 'status': 'timeout', 'limit_seconds': timeout}
        record.update(wall=time.perf_counter() - start, command=command, directory=str(target))
        manifest.append(record)
        (parent / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
