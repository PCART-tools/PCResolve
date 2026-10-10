## @package flow_probe
# Local performance probe; does not execute analyzed source or modify production code.

import argparse
import cProfile
import hashlib
import gc
import json
import os
from pathlib import Path
import platform
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.source_snapshot import SourceStore


## Measure wall and process CPU duration for one action.
#  @param action Callable to execute.
#  @return Action result and timing record.
def timed(action):
    wall, cpu = time.perf_counter(), time.process_time()
    result = action()
    return result, {'wall_seconds': time.perf_counter() - wall,
                    'cpu_seconds': time.process_time() - cpu}


## Flow analyzer recording the complete source-index phase.
class TimedAnalyzer(FlowAnalyzer):
    def _index(self):
        result, self.index_timing = timed(super()._index)
        return result


## Count records grouped by one field.
#  @param values Dictionary or object records.
#  @param field Grouping field name.
#  @return Counts by field value.
def counts(values, field):
    result = {}
    for value in values:
        key = (value.get(field, 'unspecified') if isinstance(value, dict)
               else getattr(value, field, 'unspecified'))
        result[key] = result.get(key, 0) + 1
    return result


## Parse and validate probe arguments.
#  @return Parsed argument namespace.
def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument('--source', action='append', help='Repeat for explicit files.')
    sources.add_argument('--project-root', help='Scan a source directory.')
    parser.add_argument('--import-root', action='append', default=[])
    parser.add_argument('--entry', required=True, help='module:qualified_function')
    parser.add_argument('--depth', type=int, default=3)
    parser.add_argument('--repeat', type=int, default=2,
                        help='Analyze repeatedly with the same analyzer.')
    parser.add_argument('--trace-repeat', type=int, default=2)
    parser.add_argument('--parameter', action='append',
                        help='Repeat for parameters; omit to trace every entry parameter.')
    parser.add_argument('--max-functions', type=int, default=500)
    parser.add_argument('--max-call-contexts', type=int, default=2000)
    parser.add_argument('--profile-prefix', help='Optional cProfile output prefix; adds overhead.')
    parser.add_argument('--gc-stats', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if ':' not in args.entry:
        parser.error('--entry must be module:qualified_function')
    if min(args.depth, args.repeat, args.trace_repeat, args.max_functions,
           args.max_call_contexts) < 1:
        parser.error('Depth, repetition counts, and budgets must be positive.')
    return args


## Measure analysis, indexing and repeated parameter queries.
#  @return None.
def main():
    args = parse_args()
    gc_events, gc_started = [], {}
    if args.gc_stats:
        def record_gc(phase, info):
            generation = info['generation']
            if phase == 'start':
                gc_started[generation] = time.perf_counter()
            else:
                gc_events.append({'generation': generation,
                                  'wall': time.perf_counter() - gc_started[generation],
                                  'collected': info['collected']})
        gc.callbacks.append(record_gc)
    module, qualname = args.entry.split(':', 1)
    entry = FunctionRef(module=module, qualname=qualname)
    options = {'import_roots': args.import_root or None}
    if args.source:
        options['source_files'] = args.source
    else:
        options['project_root'] = args.project_root
    analyzer, construction = timed(lambda: TimedAnalyzer(**options))
    source_timings = []
    original_snapshot = SourceStore.snapshot

    def measured_snapshot(self, *pos, **kw):
        result, timing = timed(lambda: original_snapshot(self, *pos, **kw))
        source_timings.append(timing)
        return result

    SourceStore.snapshot = measured_snapshot
    report = {'python': sys.version, 'platform': platform.platform(),
              'pid': os.getpid(), 'entry': args.entry,
              'source_files': sorted(analyzer.files),
              'import_roots': analyzer.roots,
              'depth': args.depth, 'max_functions': args.max_functions,
              'max_call_contexts': args.max_call_contexts,
              'profile_enabled': bool(args.profile_prefix),
              'construction': construction, 'runs': [],
              'notes': [
                  'Construction includes project scanning, not source parsing/indexing.',
                  'Index timing is a subset of analyze timing; do not add them.',
                  'Repeat 1 is cold only for this analyzer, not OS filesystem caches.',
                  'Later repeats may reuse source indexes; query summaries remain fresh.',
                  'to_dict/JSON serialization is timed separately from analysis.',
                  'trace_parameter queries entry-to-return flow, not all forwarding edges.',
                  'No result cache, production code changes, or runtime source execution.']}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')

    save()
    for repetition in range(1, args.repeat + 1):
        gc_begin = len(gc_events)
        profiler = cProfile.Profile() if args.profile_prefix else None
        if profiler:
            profiler.enable()
        try:
            snapshot, analysis = timed(lambda: analyzer.analyze(
                entry, max_depth=args.depth, max_functions=args.max_functions,
                max_call_contexts=args.max_call_contexts))
        finally:
            if profiler:
                profiler.disable()
                profile_path = Path('%s.analyze-%s.prof' % (args.profile_prefix, repetition))
                profile_path.parent.mkdir(parents=True, exist_ok=True)
                profiler.dump_stats(str(profile_path))
        encoded, serialization = timed(lambda: json.dumps(
            snapshot.to_dict(), sort_keys=True, ensure_ascii=False).encode('utf-8'))
        row = {'repetition': repetition, 'analyze': analysis,
               'index': analyzer.index_timing,
               'source_snapshot': source_timings[-1],
               'gc_events_during_analysis': gc_events[gc_begin:],
               'analyze_excluding_index': {
                   key: analysis[key] - analyzer.index_timing[key] for key in analysis},
               'serialize': serialization,
               'json_bytes': len(encoded),
               'snapshot_sha256': hashlib.sha256(encoded).hexdigest(),
               'function_count': len(snapshot.functions),
               'call_count': len(snapshot.calls),
               'boundary_count': len(snapshot.boundaries),
               'boundaries': counts(snapshot.boundaries, 'reason'),
               'targets': counts(snapshot.calls, 'target_status'),
               'bindings': counts(snapshot.calls, 'binding_status'),
               'parameter_flow_statuses': counts(
                   [item for call in snapshot.calls for item in call.parameter_flows], 'status'),
               'context_summary_count': len(analyzer._context_summaries),
               'context_call_count': analyzer._context_call_count,
               'source_error_count': len(analyzer.index_boundaries),
               'traces': []}
        report['runs'].append(row)
        save()
        selected = next(item for item in snapshot.functions
                        if item['function']['qualname'] == snapshot.entry.qualname
                        and item['function']['file_path'] == snapshot.entry.file_path
                        and item['function']['lineno'] == snapshot.entry.lineno)
        for parameter in args.parameter or selected['parameters']:
            for trace_repetition in range(1, args.trace_repeat + 1):
                if profiler:
                    profiler = cProfile.Profile()
                    profiler.enable()
                try:
                    traced, timing = timed(lambda: snapshot.trace_parameter(parameter))
                finally:
                    if profiler:
                        profiler.disable()
                        profile_path = Path('%s.trace-%s-%s-%s.prof' % (
                            args.profile_prefix, repetition, parameter, trace_repetition))
                        profiler.dump_stats(str(profile_path))
                row['traces'].append({
                    'parameter': parameter, 'repetition': trace_repetition,
                    'timing': timing, 'status': traced['status'],
                    'return_path_count': len(traced['return_paths']),
                    'summary_status': traced['summary_status'],
                    'summary_iterations': traced['summary_iterations'],
                    'boundary_count': len(traced['boundaries']),
                    'boundaries': counts(traced['boundaries'], 'reason')})
                save()
        print(json.dumps({'repetition': repetition, 'analyze': analysis,
                          'index': analyzer.index_timing,
                          'functions': len(snapshot.functions),
                          'calls': len(snapshot.calls)}, ensure_ascii=False), flush=True)
    print(str(args.output.resolve()))


if __name__ == '__main__':
    main()
