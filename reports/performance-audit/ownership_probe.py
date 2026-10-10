## @package reports.performance_audit.ownership_probe
#  Measure current ownership phases without changing production algorithms.

import argparse
from collections import Counter
import cProfile
import ctypes
from functools import wraps
import hashlib
import gc
import json
import os
from pathlib import Path
import platform
import sys
import time


REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'src'))


## Read process working-set and private-commit counters when available.
#  @return Mapping of byte counters; unavailable platforms return an empty map.
def memory_usage():
    if os.name != 'nt':
        return {}

    class Counters(ctypes.Structure):
        _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
                    ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                    ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                    ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                    ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t),
                    ('PrivateUsage', ctypes.c_size_t)]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    handle = ctypes.windll.kernel32.GetCurrentProcess
    handle.restype = ctypes.c_void_p
    query = ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
    if not query(handle(), ctypes.byref(counters), counters.cb):
        return {}
    return {name: int(getattr(counters, field)) for name, field in (
        ('rss', 'WorkingSetSize'), ('peak_rss', 'PeakWorkingSetSize'),
        ('private_commit', 'PrivateUsage'), ('peak_commit', 'PeakPagefileUsage'))}


## Run one fresh-process measurement and save phase events and complete output.
#  @return None.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--proofs', action='store_true')
    parser.add_argument('--gc-stats', action='store_true')
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--variant', choices=('baseline', 'empty-arguments'), default='baseline')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    events = []
    event_stream = (args.out / 'events.jsonl').open('w', encoding='utf-8')
    started_wall, started_cpu = time.perf_counter(), time.process_time()
    profiler = cProfile.Profile() if args.profile else None
    gc_events, gc_started = [], {}
    if args.gc_stats:
        def record_gc(kind, info):
            generation = info['generation']
            if kind == 'start':
                gc_started[generation] = time.perf_counter()
            else:
                gc_events.append({'generation': generation,
                                  'wall': time.perf_counter() - gc_started[generation],
                                  'collected': info['collected']})
        gc.callbacks.append(record_gc)

    def event(kind, name, **extra):
        record = {'kind': kind, 'phase': name, 'at_wall': time.perf_counter() - started_wall,
                  'at_cpu': time.process_time() - started_cpu, **extra}
        event_stream.write(json.dumps(record) + '\n')
        event_stream.flush()
        return record

    def phase(name, callback):
        wall, cpu = time.perf_counter(), time.process_time()
        event('begin', name)
        try:
            return callback()
        finally:
            record = event('end', name, wall=time.perf_counter() - wall,
                           cpu=time.process_time() - cpu, memory=memory_usage())
            events.append(record)

    def load():
        from pcresolve import ProjectAnalyzer
        from pcresolve.module_mapper import ModuleMapper
        from pcresolve.single_file import SingleFileAnalyzer
        from pcresolve.source_snapshot import SourceStore
        from pcresolve.views import build_full_view, build_summary_view
        return ProjectAnalyzer, ModuleMapper, SingleFileAnalyzer, SourceStore, build_full_view, build_summary_view

    ProjectAnalyzer, ModuleMapper, SingleFileAnalyzer, SourceStore, build_full_view, build_summary_view = phase('imports', load)
    skipped_escape_queries = 0
    if args.variant == 'empty-arguments':
        original_escape = ProjectAnalyzer._callable_field_receiver_escapes

        def escape_nonempty(self, module, source, arguments, tracers):
            nonlocal skipped_escape_queries
            if not arguments:
                skipped_escape_queries += 1
                return False
            return original_escape(self, module, source, arguments, tracers)

        ProjectAnalyzer._callable_field_receiver_escapes = escape_nonempty

    def instrument(cls, method, label):
        original = getattr(cls, method)

        @wraps(original)
        def measured(self, *pos, **kw):
            name = label(self) if callable(label) else label
            return phase(name, lambda: original(self, *pos, **kw))

        setattr(cls, method, measured)

    instrument(ModuleMapper, 'scan_project', 'scan')
    instrument(SourceStore, 'snapshot', 'source_read_parse')
    instrument(SingleFileAnalyzer, 'visit_Module', lambda self: 'visit:' + str(self.module_name))
    for name in ('_bind_bounded_local_call_results', '_bind_bounded_callback_map_results',
                 '_bind_bounded_local_iteration_results', '_bind_proven_result_method_results',
                 'resolve_cross_file_symbols', 'get_calls', '_build_symbol_provenance',
                 '_build_decorator_index', '_build_file_analysis', '_build_all_api_calls',
                 '_build_library_usage'):
        instrument(ProjectAnalyzer, name, name)

    proof_counts = Counter()
    proof_max_queries = Counter()
    expensive_proofs = []

    if args.proofs:
        def proof_wrapper(name, original):
            @wraps(original)
            def measured(self, *pos, **kw):
                budget = self._ownership_proof_budget
                root = budget.depth == 0
                if root:
                    started = time.process_time()
                try:
                    return original(self, *pos, **kw)
                finally:
                    if root:
                        duration = time.process_time() - started
                        proof_counts[name + ':roots'] += 1
                        proof_counts[name + ':queries'] += budget.queries
                        proof_counts[name + ':exhausted'] += int(budget.exhausted)
                        proof_max_queries[name] = max(proof_max_queries[name], budget.queries)
                        if duration > 0.02:
                            item = {'method': name, 'cpu': duration,
                                'queries': budget.queries, 'exhausted': budget.exhausted,
                                'module': pos[0] if pos and isinstance(pos[0], str) else '',
                                'source_kind': type(pos[1]).__name__ if len(pos) > 1 else '',
                                'source_name': pos[1][:120] if len(pos) > 1 and isinstance(pos[1], str) else ''}
                            expensive_proofs.append(item)
                            if duration > 1:
                                event('slow_proof', name, **{key: value for key, value in item.items() if key != 'method'})
            return measured

        for name in dir(ProjectAnalyzer):
            method = getattr(ProjectAnalyzer, name)
            code = getattr(method, '__code__', None)
            if code is not None and code.co_name == 'bounded' and code.co_filename.endswith('ownership_model.py'):
                setattr(ProjectAnalyzer, name, proof_wrapper(name, method))

    analyzer = ProjectAnalyzer(str(args.source.resolve()))
    if profiler:
        profiler.enable()
    runs = []
    for number in range(args.repeat):
        gc_begin = len(gc_events)
        begin = len(events)
        result = phase('analysis', analyzer.analyze)
        analysis_gc = gc_events[gc_begin:]
        if profiler:
            profiler.dump_stats(str(args.out / 'analysis.pstats'))
        view = phase('full_view', lambda: build_full_view(result))
        payload = phase('json_encode', lambda: json.dumps(view, indent=2, ensure_ascii=False))
        phase('json_write', lambda: (args.out / ('output-%s.json' % number)).write_text(payload + '\n', encoding='utf-8'))
        run_events = events[begin:]
        phases = {}
        for item in run_events:
            key = 'single_file_visit' if item['phase'].startswith('visit:') else item['phase']
            total = phases.setdefault(key, {'wall': 0.0, 'cpu': 0.0, 'count': 0})
            for clock in ('wall', 'cpu'):
                total[clock] += item[clock]
            total['count'] += 1
        runs.append({'phases': phases, 'modules': len(result.files), 'calls': len(result.all_api_calls),
            'gc_events_during_analysis': analysis_gc,
            'provenance': len(result.all_symbol_provenance), 'diagnostics': len(result.diagnostics),
            'output_bytes': len(payload.encode('utf-8')), 'sha256': hashlib.sha256(payload.encode('utf-8')).hexdigest(),
            'memory': memory_usage()})
        del view, payload
    # Summary cost is measured after the complete analysis; it does not replace it.
    summary = phase('summary_view', lambda: build_summary_view(result))
    summary_payload = phase('summary_encode', lambda: json.dumps(summary, indent=2, ensure_ascii=False))
    if profiler:
        profiler.disable()
        profiler.dump_stats(str(args.out / 'full.pstats'))
    event_stream.close()
    report = {'source': str(args.source.resolve()), 'python': sys.version, 'platform': platform.platform(),
              'python_hash_seed': os.environ.get('PYTHONHASHSEED', 'random'),
              'profiled': args.profile, 'proof_instrumented': args.proofs, 'variant': args.variant,
              'skipped_escape_queries': skipped_escape_queries, 'runs': runs, 'events': events,
              'summary_bytes': len(summary_payload.encode('utf-8')), 'memory': memory_usage(),
              'process_wall': time.perf_counter() - started_wall, 'process_cpu': time.process_time() - started_cpu,
              'proof_counts': dict(proof_counts), 'proof_max_queries': dict(proof_max_queries),
              'slow_proofs': sorted(expensive_proofs, key=lambda item: item['cpu'], reverse=True)[:40]}
    (args.out / 'metrics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'out': str(args.out), 'runs': [{k: v for k, v in run.items() if k != 'phases'} for run in runs],
                      'process_wall': report['process_wall'], 'process_cpu': report['process_cpu']}), flush=True)


if __name__ == '__main__':
    main()
