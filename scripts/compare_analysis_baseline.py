## @package compare_analysis_baseline
#  Capture public outputs before internal migrations; source is never executed.

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from pcresolve import FlowAnalyzer, FunctionRef, analyze_project
from pcresolve.ownership.views import build_full_view
from evaluate_value_flow_matrix import load_cases


ROOT = Path(__file__).resolve().parents[1]


def _fingerprint(payload):
    data = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(data).hexdigest()


_PATH_FIELDS = frozenset(('file_path', 'source_files', 'import_roots', 'source',
                          'id', 'call_context', 'call_id', 'incoming_call_id',
                          'output_container', 'object_sources', 'target_container'))
_PATH_KEY_FIELDS = frozenset(('sha256', 'source_hashes'))


def _canonicalize_paths(value, root, field=''):
    """Canonicalize checkout-local paths in documented flow output fields."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            mapped = _canonicalize_paths(key, root, 'file_path') if field in _PATH_KEY_FIELDS else key
            if mapped in result:
                raise ValueError('Path normalization produced a duplicate key: %s' % mapped)
            result[mapped] = _canonicalize_paths(item, root, key)
        return result
    if isinstance(value, list):
        return [_canonicalize_paths(item, root, field) for item in value]
    if not isinstance(value, str) or field not in _PATH_FIELDS:
        return value
    prefix = '$heap:' if value.startswith('$heap:') else ''
    candidate = value[len(prefix):].replace('\\', '/')
    normalized_root = str(root).replace('\\', '/').rstrip('/')
    if candidate.casefold() == normalized_root.casefold():
        return prefix + '$ROOT'
    if candidate.casefold().startswith(normalized_root.casefold() + '/'):
        return prefix + '$ROOT' + candidate[len(normalized_root):]
    return value


## Validate corpus availability and inventory before producing any baseline.
#  @param root Repository root.
#  @param projects Ownership project manifest.
#  @param cases Loaded flow cases and their fixture directories.
#  @param expected_ownership Required ownership project count.
#  @param expected_flow Required flow entry count.
#  @return None; incomplete inputs raise ValueError.
def validate_inputs(root, projects, cases, expected_ownership=42, expected_flow=83):
    for name, project in projects.items():
        path = root / project['path']
        if not path.is_dir() or not any(path.rglob('*.py')):
            raise ValueError('Missing or empty ownership corpus: %s' % name)
    for directory, case in cases:
        if not directory.is_dir():
            raise ValueError('Missing flow corpus: %s' % case['id'])
        files = case.get('files')
        if files is not None:
            for name in files:
                if not (directory / name).is_file():
                    raise ValueError('Missing flow source: %s: %s' % (case['id'], name))
        elif not any(directory.rglob('*.py')):
            raise ValueError('Missing flow source: %s' % case['id'])
    if len(projects) != expected_ownership or len(cases) != expected_flow:
        raise ValueError('Incomplete baseline inventory: ownership=%s flow=%s' %
                         (len(projects), len(cases)))


## Capture ownership and flow outputs on the established regression corpora.
#  @return Output fingerprints, inventory counts, and separately measured timings.
def capture_baseline():
    outputs, counts, timings = {}, {}, {}
    package = ROOT / 'src' / 'pcresolve'
    source_hash = hashlib.sha256()
    for path in sorted(package.rglob('*.py')):
        source_hash.update(path.relative_to(package).as_posix().encode('utf-8'))
        source_hash.update(path.read_bytes())
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                              capture_output=True, text=True)
    manifest = json.loads((ROOT / 'ground_truth/projects.json').read_text(encoding='utf-8'))
    cases = load_cases()
    validate_inputs(ROOT, manifest['projects'], cases)
    for name, project in sorted(manifest['projects'].items()):
        start = time.perf_counter()
        result = analyze_project(str(ROOT / project['path']))
        key = 'ownership/' + name
        outputs[key] = _fingerprint(build_full_view(result))
        counts[key] = len(result.all_api_calls)
        timings[key] = time.perf_counter() - start
    for project, case in cases:
        contracts = ({case['module'] + '.' + case['entry']: {
            'parameters': case['parameter_shapes'],
            'provenance': 'Reviewed matrix contract: ' + case['id']}}
            if case.get('parameter_shapes') else None)
        start = time.perf_counter()
        files = case.get('files')
        analyzer = (FlowAnalyzer(source_files=[project / p for p in files],
                                 import_roots=[project], parameter_shapes=contracts)
                    if files is not None else FlowAnalyzer(
                        project_root=project, parameter_shapes=contracts))
        result = analyzer.analyze(FunctionRef(module=case['module'], qualname=case['entry']),
                                  max_depth=case.get('max_depth', 3),
                                  max_functions=case.get('max_functions', 500),
                                  max_call_contexts=case.get('max_call_contexts', 2000))
        payload = {'analysis': result.to_dict(),
                   'queries': {p: result.trace_parameter(p) for p in case.get('returns', {})}}
        key = 'flow/' + case['id']
        outputs[key] = _fingerprint(_canonicalize_paths(payload, ROOT))
        counts[key] = len(result.calls)
        timings[key] = time.perf_counter() - start
    return {'python': platform.python_version(), 'hash_seed': os.environ.get('PYTHONHASHSEED'),
            'path_normalization': 'flow-checkout-root-v2',
            'revision': revision.stdout.strip(), 'source_sha256': source_hash.hexdigest(),
            'outputs': outputs,
            'call_counts': counts, 'seconds': timings}


## Capture or compare snapshots on the same checkout path and Python runtime.
#  @return Exit code, nonzero if any public output or inventory changed.
def main():
    # Existing ownership explanations can contain set-derived sequences. Fix
    # Python's hash seed before importing/using the analyzers in the child.
    if os.environ.get('PYTHONHASHSEED') != '0':
        environment = dict(os.environ, PYTHONHASHSEED='0')
        return subprocess.call([sys.executable, __file__] + sys.argv[1:], env=environment)
    parser = argparse.ArgumentParser(description='Compare public analysis outputs during refactoring')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    previous = None
    if args.compare:
        if args.output.resolve() == args.compare.resolve():
            parser.error('--output must differ from the comparison reference')
        previous = json.loads(args.compare.read_text(encoding='utf-8'))
    current = capture_baseline()
    if previous is not None:
        if previous['python'] != current['python']:
            parser.error('Use the same Python runtime for baseline comparisons')
        if previous.get('hash_seed') != current['hash_seed']:
            parser.error('Recapture the baseline with this script to fix the Python hash seed')
        if previous.get('path_normalization') != current.get('path_normalization'):
            parser.error('Baseline and current path normalization must match')
    args.output.write_text(json.dumps(current, indent=2) + '\n', encoding='utf-8')
    print('Captured %s ownership projects and %s flow entries.' % (
        sum(k.startswith('ownership/') for k in current['outputs']),
        sum(k.startswith('flow/') for k in current['outputs'])))
    if previous is not None:
        changed = sorted(k for k in set(previous['outputs']) | set(current['outputs'])
                         if previous['outputs'].get(k) != current['outputs'].get(k)
                         or previous['call_counts'].get(k) != current['call_counts'].get(k))
        print('Changed outputs: %s' % len(changed))
        for key in changed:
            print(key)
        return int(bool(changed))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
