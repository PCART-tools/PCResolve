## @package evaluate_value_flow_matrix
# Reproducible semantic probes. Fixture programs are parsed, never executed.
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests' / 'fixtures' / 'value_flow_matrix'
FAILURES = {'positive_missing', 'negative_flow_reported', 'mismatch', 'unresolved', 'error'}


## Load reviewed expectations from independent mini-projects.
#  @param root Directory containing manifests.
#  @return Ordered pairs of project directory and case specification.
def load_cases(root=FIXTURES):
    cases, seen = [], set()
    for path in sorted(Path(root).rglob('manifest.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        if manifest['version'] != 1:
            raise ValueError('Unsupported manifest version: ' + str(path))
        for case in manifest['cases']:
            for field in ('id', 'category', 'module', 'entry', 'rationale'):
                if not isinstance(case.get(field), str) or not case[field]:
                    raise ValueError('Missing case field: ' + field)
            if case['id'] in seen:
                raise ValueError('Duplicate case id: ' + case['id'])
            if any(type(v) is not bool for v in case.get('returns', {}).values()):
                raise ValueError('Return expectations must be booleans: ' + case['id'])
            if any(not isinstance(name, str) or not isinstance(shape, str)
                   for name, shape in case.get('parameter_shapes', {}).items()):
                raise ValueError('Parameter shapes must be strings: ' + case['id'])
            for call in case.get('calls', []):
                occurrence = call.get('occurrence', 0)
                if type(occurrence) is not int or occurrence < 0:
                    raise ValueError('Invalid call occurrence: ' + case['id'])
            seen.add(case['id'])
            cases.append((path.parent, case))
    return cases


def _checks(case):
    if case.get('inventory', True) and 'max_call_contexts' not in case:
        yield 'call_inventory', 'lexical_calls', True, None
    for parameter, expected in case.get('returns', {}).items():
        yield 'entry_return', parameter, expected, None
    for index, call in enumerate(case.get('calls', [])):
        prefix = '%s#%s' % (call['name'], call.get('occurrence', 0))
        yield 'call_presence', prefix, True, index
        if 'target' in call:
            yield 'target', prefix, call['target'], index
        for slot, formal in call.get('bindings', {}).items():
            yield 'binding', prefix + ':' + slot, formal, index
        for source, target, expected in call.get('flows', []):
            yield 'parameter_flow', prefix + ':' + source + '->' + target, expected, index
        for source, target, expected in call.get('receiver_flows', []):
            yield 'receiver_flow', prefix + ':' + source + '->' + target, expected, index
        if 'return_flow' in call:
            yield 'call_return', prefix, call['return_flow'], index
    for reason in case.get('boundaries', {}).get('required', []):
        yield 'boundary', reason, True, None
    for reason in case.get('boundaries', {}).get('forbidden', []):
        yield 'boundary', reason, False, None


def _slot(argument):
    if not isinstance(argument, dict):
        return 'receiver' if argument == 'receiver' else None
    if 'receiver' in argument:
        return 'receiver'
    if 'position' in argument:
        return str(argument['position'])
    return 'kw:' + str(argument.get('keyword'))


def _inventory(result):
    tree = ast.parse(Path(result.entry.file_path).read_text(encoding='utf-8-sig'))
    node = next(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.lineno == result.entry.lineno)
    expected = []
    def visit(item):
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for default in item.args.defaults + [v for v in item.args.kw_defaults if v is not None]:
                visit(default)
            for decorator in getattr(item, 'decorator_list', []):
                visit(decorator)
            return
        if isinstance(item, ast.ClassDef):
            for expression in item.bases + [k.value for k in item.keywords] + item.decorator_list:
                visit(expression)
            return
        if isinstance(item, ast.Call):
            expected.append((item.lineno, item.col_offset, ast.unparse(item.func)))
        for child in ast.iter_child_nodes(item):
            visit(child)
    for statement in node.body:
        visit(statement)
    actual = [(c.lineno, c.col_offset, c.callee_name) for c in result.find_calls(caller=result.entry)]
    missing = Counter(expected) - Counter(actual)
    extra = Counter(actual) - Counter(expected)
    return {'expected_count': len(expected), 'actual_count': len(actual),
            'missing': sorted(missing.elements()), 'extra': sorted(extra.elements())}


def _outcome(dimension, expected, actual):
    if dimension in ('entry_return', 'parameter_flow', 'receiver_flow', 'call_return'):
        if expected:
            return 'positive_found' if actual else 'positive_missing'
        return 'negative_flow_reported' if actual else 'negative_no_path'
    if actual is None and expected is not None:
        return 'unresolved'
    return 'matched' if expected == actual else 'mismatch'


## Evaluate all declared checks, preserving failures and analysis exceptions.
#  @param project Mini-project source root.
#  @param case Frozen semantic and boundary expectations.
#  @return One case result with deterministic checks and diagnostic counters.
def evaluate_case(project, case):
    project = Path(project)
    planned = list(_checks(case))
    rows = []
    diagnostic = {'boundaries': {}, 'queries': {}, 'calls': []}
    start = time.perf_counter()
    try:
        source_files = case.get('files')
        shape_contracts = ({case['module'] + '.' + case['entry']: {
            'parameters': case['parameter_shapes'],
            'provenance': 'Reviewed matrix contract: ' + case['id']}}
            if case.get('parameter_shapes') else None)
        analyzer = (FlowAnalyzer(source_files=[project / p for p in source_files],
                                 import_roots=[project], parameter_shapes=shape_contracts)
                    if source_files is not None else FlowAnalyzer(
                        project_root=project, parameter_shapes=shape_contracts))
        result = analyzer.analyze(FunctionRef(module=case['module'], qualname=case['entry']),
                                  max_depth=case.get('max_depth', 3),
                                  max_functions=case.get('max_functions', 500),
                                  max_call_contexts=case.get('max_call_contexts', 2000))
        reasons = Counter(b['reason'] for b in result.boundaries)
        diagnostic['boundaries'] = dict(sorted(reasons.items()))
        selected = []
        for specification in case.get('calls', []):
            calls = result.find_calls(caller=result.entry, callee_name=specification['name'])
            occurrence = specification.get('occurrence', 0)
            call = calls[occurrence] if len(calls) > occurrence else None
            selected.append(call)
            diagnostic['calls'].append({'name': specification['name'], 'occurrence': occurrence,
                'lineno': call.lineno if call else None,
                'target_status': call.target_status if call else 'call_missing',
                'analysis_status': call.analysis_status if call else 'call_missing'})
        queries = {}
        for dimension, subject, expected, index in planned:
            error = None
            try:
                call = selected[index] if index is not None else None
                binding_unavailable = False
                if dimension == 'call_inventory':
                    inventory = _inventory(result)
                    diagnostic['inventory'] = inventory
                    actual = not inventory['missing'] and not inventory['extra']
                elif dimension == 'entry_return':
                    query = queries.setdefault(subject, result.trace_parameter(subject))
                    actual = bool(query['return_paths'])
                    diagnostic['queries'][subject] = {
                        'status': query['status'], 'summary_status': query['summary_status'],
                        'summary_iterations': query['summary_iterations'],
                        'boundary_reasons': sorted({b['reason'] for b in query['boundaries']})}
                elif dimension == 'boundary':
                    actual = subject in reasons
                elif dimension == 'call_presence':
                    actual = call is not None
                elif call is None:
                    actual = None
                elif dimension == 'target':
                    actual = call.target.module + ':' + call.target.qualname if call.target else None
                elif dimension == 'binding':
                    spec = case['calls'][index]
                    prefix = '%s#%s:' % (spec['name'], spec.get('occurrence', 0))
                    slot = subject[len(prefix):]
                    bindings = {b['parameter'] for b in call.parameter_bindings
                                if _slot(b.get('argument')) == slot and b.get('status') == 'exact'}
                    if slot.startswith('default:'):
                        bindings.update(b['parameter'] for b in call.parameter_bindings
                                        if b.get('binding_kind') == 'default'
                                        and b.get('status') == 'exact' and b['parameter'] == slot[8:])
                    if slot == 'receiver':
                        bindings.update(b['parameter'] for b in call.argument_sources
                                        if _slot(b.get('argument')) == slot)
                    actual = next(iter(bindings)) if len(bindings) == 1 else None
                elif dimension in ('parameter_flow', 'receiver_flow'):
                    spec = case['calls'][index]
                    prefix = '%s#%s:' % (spec['name'], spec.get('occurrence', 0))
                    source, formal = subject[len(prefix):].split('->')
                    if dimension == 'receiver_flow':
                        binding_unavailable = not any(_slot(arg['argument']) == 'receiver' and
                                                      arg['parameter'] == formal for arg in call.argument_sources)
                        actual = any(v.get('kind') == 'parameter' and v['source'] == source
                                     for arg in call.argument_sources if _slot(arg['argument']) == 'receiver'
                                     and arg['parameter'] == formal for v in arg['sources'])
                    else:
                        binding_unavailable = not any(b.get('status') == 'exact' and b['parameter'] == formal
                                                      for b in call.parameter_bindings)
                        actual = any(v['source_parameter'] == source and v['target_parameter'] == formal
                                     for v in call.parameter_flows)
                else:
                    actual = bool(call.return_flows)
                unavailable = (index is not None and call is None and dimension != 'call_presence') or (
                    binding_unavailable and actual is False)
                outcome = 'unresolved' if unavailable else _outcome(dimension, expected, actual)
            except Exception as exc:
                actual, outcome, error = None, 'error', type(exc).__name__ + ': ' + str(exc)
            row = {'id': case['id'] + '/' + dimension + '/' + subject,
                   'dimension': dimension, 'subject': subject, 'expected': expected,
                   'actual': actual, 'outcome': outcome}
            if error:
                row['error'] = error
            rows.append(row)
    except Exception as exc:
        diagnostic['error'] = type(exc).__name__ + ': ' + str(exc)
        rows = [{'id': case['id'] + '/' + dim + '/' + name, 'dimension': dim,
                 'subject': name, 'expected': exp, 'actual': None, 'outcome': 'error'}
                for dim, name, exp, _ in planned]
    return {'id': case['id'], 'category': case['category'], 'rationale': case['rationale'],
            'checks': rows, 'diagnostic': diagnostic,
            'seconds': round(time.perf_counter() - start, 6)}


## Aggregate dimensions without counting unknown absence as proven no-flow.
#  @param results Individual case results.
#  @return Counts per dimension, including errors and unresolved checks.
def summarize(results):
    dimensions = {}
    for result in results:
        for row in result['checks']:
            counts = dimensions.setdefault(row['dimension'], Counter())
            counts['checks'] += 1
            counts[row['outcome']] += 1
    return {key: dict(sorted(value.items())) for key, value in sorted(dimensions.items())}


## Evaluate all cases and capture exact input and analyzer provenance.
#  @param root Root containing manifests and source mini-projects.
#  @return JSON-safe report with all checks and failures.
def evaluate(root=FIXTURES):
    root = Path(root)
    cases = load_cases(root)
    results = [evaluate_case(project, case) for project, case in cases]
    revision = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(root.rglob('*')) if p.suffix in ('.py', '.json') and '__pycache__' not in p.parts}
    return {'schema_version': 'flow-eval-1', 'case_count': len(cases),
            'revision': revision.stdout.strip(), 'python': platform.python_version(),
            'analyzer_sha256': hashlib.sha256((ROOT / 'src/pcresolve/flow.py').read_bytes()).hexdigest(),
            'evaluator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'input_sha256': hashes, 'dimensions': summarize(results), 'results': results}


## Render a human-readable report without hiding any failing check.
#  @param report The complete evaluation result.
#  @return Markdown text with dimension counts and per-case failures.
def render_markdown(report):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    lines = ['# Value-flow evaluation matrix', '',
             'Analyzer revision: `%s`; Python: `%s`.' % (report['revision'], report['python']), '',
             '%s entry cases. Semantic gold is manually specified; unknown absence is not a no-flow proof.' % report['case_count'], '',
             '| Dimension | Checks | Outcomes |', '|---|---:|---|']
    for name, counts in report['dimensions'].items():
        outcomes = ', '.join('%s=%s' % (k, v) for k, v in counts.items() if k != 'checks')
        lines.append('| %s | %s | %s |' % (name, counts['checks'], outcomes))
    lines += ['', '## Cases', '', '| Case | Category | Checks | Gaps |', '|---|---|---:|---:|']
    for result in report['results']:
        gaps = sum(r['outcome'] in FAILURES for r in result['checks'])
        lines.append('| %s | %s | %s | %s |' % (result['id'], result['category'], len(result['checks']), gaps))
    lines += ['', '## Failing or unresolved checks', '',
              'Multiple checks can describe the same underlying defect. These counts are not independent defects.', '']
    for result in report['results']:
        gaps = [r for r in result['checks'] if r['outcome'] in FAILURES]
        if not gaps:
            continue
        lines += ['### ' + result['id'], '', result['rationale'], '',
                  '| Dimension | Subject | Expected | Actual | Outcome |', '|---|---|---|---|---|']
        for row in gaps:
            lines.append('| %s |' % ' | '.join(cell(row[k]) for k in ('dimension', 'subject', 'expected', 'actual', 'outcome')))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


## Run the matrix; semantic gaps yield a nonzero exit only with --strict.
#  @return None.
def main():
    parser = argparse.ArgumentParser(description='Evaluate value-flow semantic and boundary coverage')
    parser.add_argument('--root', type=Path, default=FIXTURES)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--markdown', type=Path)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    report = evaluate(args.root)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    if args.markdown:
        args.markdown.write_text(render_markdown(report), encoding='utf-8')
    print(json.dumps({'case_count': report['case_count'], 'dimensions': report['dimensions']}, indent=2))
    if args.strict and any(r['outcome'] in FAILURES for case in report['results'] for r in case['checks']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
