## @package evaluate_value_flow
# Independent, manually specified value-flow probes; no analyzer fixes here.
import argparse
from collections import Counter
import json
from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests' / 'fixtures' / 'value_flow_eval'


## Evaluate the frozen synthetic cases without treating absence as proof.
#  @return JSON-safe checks, coverage counts, and boundary diagnostics.
def evaluate():
    manifest = json.loads((FIXTURES / 'expected.json').read_text(encoding='utf-8'))
    rows, diagnostics = [], []

    def record(entry, dimension, name, expected, actual):
        if isinstance(expected, bool):
            outcome = ('positive_found' if actual else 'positive_missing') if expected else (
                'negative_flow_reported' if actual else 'negative_no_path')
        else:
            outcome = 'matched' if actual == expected else 'mismatch'
        rows.append(dict(entry=entry, dimension=dimension, name=name,
                         expected=expected, actual=actual, outcome=outcome))

    for case in manifest['cases']:
        entry = case['entry']
        result = FlowAnalyzer(project_root=FIXTURES).analyze(
            FunctionRef(module='cases', qualname=entry), max_depth=3)
        queries = {}
        for parameter, expected in case['returns'].items():
            query = result.trace_parameter(parameter)
            queries[parameter] = {'status': query['status'],
                                  'summary_status': query['summary_status']}
            record(entry, 'entry_return', parameter, expected, bool(query['return_paths']))
        if 'call' in case:
            expected = case['call']
            calls = result.find_calls(caller=result.entry, callee_name=expected['name'])
            if len(calls) != 1:
                raise ValueError('Expected one call in ' + entry)
            call = calls[0]
            target = call.target.module + ':' + call.target.qualname if call.target else None
            record(entry, 'target', call.callee_name, expected['target'], target)
            actual = {str(b['argument'].get('position', b['argument'].get('keyword'))): b['parameter']
                      for b in call.parameter_bindings if b.get('argument') is not None}
            for slot, formal in expected['bindings'].items():
                record(entry, 'binding', slot, formal, actual.get(slot))
            edges = {(v['source_parameter'], v['target_parameter']) for v in call.parameter_flows}
            for parameter in case['returns']:
                for formal in set(expected['bindings'].values()):
                    record(entry, 'parameter_flow', parameter + '->' + formal,
                           [parameter, formal] in expected['flows'], (parameter, formal) in edges)
            record(entry, 'call_return', call.callee_name, expected['returns'], bool(call.return_flows))
        diagnostics.append({'entry': entry, 'queries': queries,
                            'boundaries': dict(Counter(b['reason'] for b in result.boundaries))})
    dimensions = {}
    for dimension in sorted({r['dimension'] for r in rows}):
        checks = [r for r in rows if r['dimension'] == dimension]
        counts = Counter(r['outcome'] for r in checks)
        dimensions[dimension] = dict(counts, checks=len(checks),
            expected_positive=sum(r['expected'] is True for r in checks),
            expected_negative=sum(r['expected'] is False for r in checks))
    return {'manifest_version': manifest['version'], 'case_count': len(manifest['cases']),
            'max_depth': 3, 'dimensions': dimensions, 'results': rows, 'diagnostics': diagnostics}


## Run the evaluator and optionally save the complete report.
#  @return None.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate()
    if args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['dimensions'], indent=2))


if __name__ == '__main__':
    main()
