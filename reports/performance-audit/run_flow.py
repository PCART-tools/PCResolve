## @package reports.performance_audit.run_flow
# Serial measurements of source scope, analysis depth, and repeated flow queries.
import json
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.environ['TEMP']) / 'pcresolve-pandas-batch-repro'
OUT = Path(os.environ['TEMP']) / 'pcresolve-performance-audit' / 'flow'
OUT.mkdir(parents=True, exist_ok=True)
manifest = []
parser = argparse.ArgumentParser()
parser.add_argument('--filter', default='')
selection = parser.parse_args().filter
full = DATA / 'pandas-0.21.0'
window_batch = next(DATA.glob('step2-3-error-window-sum-*/pandas'))
timeout_batch = next(DATA.glob('step2-2-timeout-*/pandas'))
jobs = []
for label, source, entry, root in (
    ('base-single', full / 'pandas/core/indexes/base.py', 'pandas.core.indexes.base:Index.append', full),
    ('window-single', window_batch / 'core/window.py', 'pandas.core.window:Window.sum', window_batch.parent),
    ('base-plus-timeout', timeout_batch, 'pandas.core.indexes.base:Index.append', full),
    ('full-scope', full / 'pandas', 'pandas.core.indexes.base:Index.append', full)):
    for depth in (1, 3, 5):
        jobs.append((label + '-d' + str(depth), source, entry, root, depth, []))
jobs.append(('full-scope-profile', full / 'pandas', 'pandas.core.indexes.base:Index.append', full, 3,
             ['--profile-prefix', str(OUT / 'full-scope-profile'), '--repeat', '1']))
for label, source, entry, root, depth, extra in jobs:
    if selection and not label.startswith(selection):
        continue
    if label.startswith('base-plus-timeout'):
        sources = ['--source', str(full / 'pandas/core/indexes/base.py'),
                   '--import-root', str(timeout_batch.parent)]
        for file in sorted(source.rglob('*.py')):
            sources.extend(['--source', str(file)])
    else:
        sources = ['--source' if source.is_file() else '--project-root', str(source)]
    command = [sys.executable, str(ROOT / 'reports/performance-audit/flow_probe.py'),
               *sources, '--import-root', str(root), '--entry', entry, '--depth', str(depth),
               '--output', str(OUT / (label + '.json'))] + extra
    print(json.dumps({'start': label}), flush=True)
    started = time.perf_counter()
    with (OUT / (label + '.stdout.log')).open('w', encoding='utf-8') as stdout, (OUT / (label + '.stderr.log')).open('w', encoding='utf-8') as stderr:
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=stdout, stderr=stderr, timeout=180)
            status = 'ok' if result.returncode == 0 else 'error'
        except subprocess.TimeoutExpired:
            status = 'timeout'
    record = {'name': label, 'status': status, 'wall': time.perf_counter() - started, 'command': command}
    manifest.append(record)
    (OUT / ('manifest' + ('-' + selection if selection else '') + '.json')).write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(record), flush=True)
