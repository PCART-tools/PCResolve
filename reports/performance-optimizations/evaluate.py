## @package reports.performance_optimizations.evaluate
#  Serial baseline comparisons, historical slices and bounded scope probes.

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]


## Evaluate in fresh processes and retain partial results on timeouts.
#  @return None.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--group', choices=['paired', 'batches', 'scope', 'flow'], required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    batches = sorted(args.data.glob('step2-*/pandas'))
    jobs = []
    if args.group == 'paired':
        for prefix in ('step2-2-longest-', 'step2-2-timeout-'):
            source = next(p for p in batches if p.parent.name.startswith(prefix))
            for number, repo in enumerate((args.baseline, ROOT, ROOT, args.baseline)):
                jobs.append((source.parent.name + '-' + str(number), repo, source, 'ownership'))
    elif args.group == 'batches':
        jobs = [(p.parent.name, ROOT, p, 'ownership') for p in batches]
    elif args.group == 'scope':
        jobs = [('pandas-full', ROOT, args.data / 'pandas-0.21.0/pandas', 'ownership'),
                ('pcresolve-self', ROOT, ROOT / 'src/pcresolve', 'ownership'),
                ('base-single', ROOT, args.data / 'pandas-0.21.0/pandas/core/indexes/base.py', 'ownership'),
                ('allnews', ROOT, ROOT / 'tests/fixtures/tested_projects/allnews', 'ownership')]
    else:
        jobs = [('flow-' + label, repo, args.data / 'pandas-0.21.0/pandas', 'flow')
                for label, repo in (('baseline', args.baseline), ('optimized', ROOT))]
    results = []
    for name, repo, source, kind in jobs:
        target = args.out / name
        target.mkdir(parents=True, exist_ok=True)
        probe = repo / 'reports/performance-audit' / (kind + '_probe.py')
        if kind == 'ownership':
            command = [sys.executable, str(probe), str(source), '--out', str(target)]
        else:
            command = [sys.executable, str(probe), '--project-root', str(source),
                       '--import-root', str(source.parent), '--entry',
                       'pandas.core.indexes.base:Index.append', '--depth', '3',
                       '--repeat', '3', '--output', str(target / 'metrics.json')]
        print(json.dumps({'start': name, 'baseline': repo == args.baseline}), flush=True)
        start = time.perf_counter()
        with (target / 'stdout.log').open('w', encoding='utf-8') as stdout, \
                (target / 'stderr.log').open('w', encoding='utf-8') as stderr:
            try:
                process = subprocess.run(command, cwd=repo, stdout=stdout, stderr=stderr,
                                         timeout=180, env={**os.environ, 'PYTHONHASHSEED': '0'})
                status = 'ok' if process.returncode == 0 else 'error'
            except subprocess.TimeoutExpired:
                status = 'timeout'
        row = {'name': name, 'status': status, 'baseline': repo == args.baseline,
               'wall': time.perf_counter() - start, 'directory': str(target),
               'command': command, 'limit_seconds': 180}
        if status == 'ok':
            row['metrics'] = json.loads((target / 'metrics.json').read_text(encoding='utf-8'))
        results.append(row)
        (args.out / 'results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
        print(json.dumps({key: value for key, value in row.items() if key != 'metrics'}), flush=True)


if __name__ == '__main__':
    main()
