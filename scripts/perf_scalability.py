#!/usr/bin/env python3
## @package scripts.perf_scalability
#  Reproducible cold/warm/edit benchmarks without timing allocation instrumentation.

import argparse
import hashlib
import json
from pathlib import Path
import platform
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pcresolve import ProjectAnalyzer, FlowAnalyzer, FunctionRef
from pcresolve.analysis_limits import resident_memory
from pcresolve.views import build_full_view


## Generate independent modules exercising imports, factory returns and entry flows.
#  @param root Scratch project directory.
#  @param size Number of provider modules.
def generate(root, size):
    root.mkdir(parents=True, exist_ok=True)
    for index in range(size):
        (root / ('provider%04d.py' % index)).write_text(
            'import json\n'
            'class Factory:\n @staticmethod\n def make(): return Factory()\n'
            'def decode(value): return json.loads(value)\n'
            'created = Factory.make()\n', encoding='utf-8')
    (root / 'main.py').write_text(
        'from provider0000 import decode\ndef entry(value): return decode(value)\n', encoding='utf-8')


## Measure analysis separately from constructing or encoding output fingerprints.
#  @param callback Analysis operation.
#  @param flow Whether the result uses the experimental flow adapter.
#  @return Metrics and the complete public output for equivalence checks.
def measure(callback, flow=False):
    wall, cpu = time.perf_counter(), time.process_time()
    result = callback()
    row = dict(wall=time.perf_counter()-wall, cpu=time.process_time()-cpu,
               rss_after=resident_memory())
    output = result.to_dict() if flow else build_full_view(result)
    payload = json.dumps(output, ensure_ascii=False, separators=(',', ':'))
    row['sha256'] = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    row['calls'] = len(result.calls if flow else result.all_api_calls)
    return row, output


## Exercise cold, unchanged and edited sources and compare every reused result.
#  @param root Generated project root; never an existing user project.
#  @param repeats Number of repeated unchanged queries.
#  @return Independent metrics with complete-output equivalence assertions.
def run_sample(root, repeats):
    rows = []
    def record(name, callback, flow=False):
        row, output = measure(callback, flow)
        row['variant'] = name
        rows.append(row)
        return output
    owner = ProjectAnalyzer(str(root), reuse_source_facts=True)
    expected = record('ownership_cold', lambda: ProjectAnalyzer(str(root)).analyze())
    assert record('ownership_cache_cold', owner.analyze) == expected
    for _ in range(repeats):
        assert record('ownership_unchanged', owner.analyze) == expected
    flow = FlowAnalyzer(project_root=root)
    entry = FunctionRef(module='main', qualname='entry')
    query = lambda: flow.analyze(entry, max_depth=2)
    expected_flow = record('flow_cold', query, True)
    for _ in range(repeats):
        assert record('flow_unchanged', query, True) == expected_flow
    path = root / 'provider0000.py'
    path.write_text(path.read_text(encoding='utf-8').replace('json.loads(value)', 'None'), encoding='utf-8')
    changed_owner = record('ownership_one_file_edit', owner.analyze)
    assert changed_owner == record('ownership_edit_fresh', lambda: ProjectAnalyzer(str(root)).analyze())
    changed_flow = record('flow_one_file_edit', query, True)
    assert changed_flow == record('flow_edit_fresh', lambda: FlowAnalyzer(project_root=root).analyze(entry, max_depth=2), True)
    return rows


## Write measurements including runtime and implementation identities.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sizes', type=int, nargs='+', default=[10, 100, 500])
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if min(args.sizes + [args.repeats]) < 1:
        parser.error('Sizes and repeats must be positive')
    code = Path(__file__).resolve().parents[1] / 'src' / 'pcresolve'
    identity = hashlib.sha256(b''.join(path.name.encode()+path.read_bytes()
                                     for path in sorted(code.glob('*.py')))).hexdigest()
    report = dict(python=sys.version, platform=platform.platform(),
                  analyzer_sha256=identity, repeats=args.repeats, samples=[])
    with tempfile.TemporaryDirectory(prefix='pcresolve-scale-') as directory:
        scratch = Path(directory).resolve()
        for size in args.sizes:
            root = (scratch / str(size)).resolve()
            assert scratch in root.parents
            generate(root, size)
            rows = run_sample(root, args.repeats)
            sample = dict(modules=size+1, rows=rows, outputs_equal=True)
            report['samples'].append(sample)
            print(json.dumps(sample), flush=True)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
