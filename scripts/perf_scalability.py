#!/usr/bin/env python3
## @package scripts.perf_scalability
#  Reproducible cold/warm/edit benchmarks without timing allocation instrumentation.

import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from pcresolve import ProjectAnalyzer, FlowAnalyzer, FunctionRef
try:
    from pcresolve.runtime.limits import resident_memory
except ImportError:
    from pcresolve.analysis_limits import resident_memory
try:
    from pcresolve.ownership.views import build_full_view
except ImportError:
    from pcresolve.views import build_full_view


## Return this process's peak resident set size in bytes, on Windows and Unix.
def peak_rss_bytes():
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('PageFaultCount', wintypes.DWORD),
                        ('PeakWorkingSetSize', ctypes.c_size_t),
                        ('WorkingSetSize', ctypes.c_size_t),
                        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
                        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                        ('PagefileUsage', ctypes.c_size_t),
                        ('PeakPagefileUsage', ctypes.c_size_t)]
        counters = PROCESS_MEMORY_COUNTERS()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        psapi = ctypes.WinDLL('psapi', use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        handle = kernel32.GetCurrentProcess()
        ok = psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb)
        if not ok:
            raise OSError('GetProcessMemoryInfo failed')
        return int(counters.PeakWorkingSetSize)
    import resource
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == 'darwin' else peak * 1024)


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
    parser.add_argument('--independent-samples', type=int, default=5)
    parser.add_argument('--worker-size', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker_size is not None:
        with tempfile.TemporaryDirectory(prefix='pcresolve-scale-worker-') as directory:
            root = Path(directory).resolve() / 'project'
            generate(root, args.worker_size)
            rows = run_sample(root, args.repeats)
        print(json.dumps(dict(modules=args.worker_size + 1, rows=rows,
                              peak_rss_bytes=peak_rss_bytes(), outputs_equal=True)))
        return
    if min(args.sizes + [args.repeats, args.independent_samples]) < 1:
        parser.error('Sizes, repeats and independent samples must be positive')
    code = Path(__file__).resolve().parents[1] / 'src' / 'pcresolve'
    identity = hashlib.sha256(b''.join(path.relative_to(code).as_posix().encode()+path.read_bytes()
                                     for path in sorted(code.rglob('*.py')))).hexdigest()
    report = dict(python=sys.version, platform=platform.platform(),
                  analyzer_sha256=identity, repeats=args.repeats,
                  independent_samples=args.independent_samples, samples=[])
    for size in args.sizes:
        runs = []
        for _ in range(args.independent_samples):
            command = [sys.executable, str(Path(__file__).resolve()),
                       '--worker-size', str(size), '--repeats', str(args.repeats)]
            completed = subprocess.run(command, check=True, capture_output=True, text=True)
            runs.append(json.loads(completed.stdout.strip().splitlines()[-1]))
        peaks = [run['peak_rss_bytes'] for run in runs]
        sample = dict(modules=size+1, runs=runs, outputs_equal=all(r['outputs_equal'] for r in runs),
                      peak_rss_bytes_median=int(statistics.median(peaks)),
                      peak_rss_bytes_min=min(peaks), peak_rss_bytes_max=max(peaks))
        report['samples'].append(sample)
        print(json.dumps(sample), flush=True)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
