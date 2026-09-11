import importlib.util
import json
from pathlib import Path


def load_runner():
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'evaluate_value_flow_matrix.py'
    spec = importlib.util.spec_from_file_location('matrix_runner', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_call_is_unresolved_not_negative_success(tmp_path):
    runner = load_runner()
    (tmp_path / 'sample.py').write_text('def entry(x):\n    return x\n')
    case = {'id': 'missing', 'category': 'runner', 'module': 'sample', 'entry': 'entry',
            'rationale': 'Runner must not treat missing call as proof of no flow.',
            'returns': {'x': True}, 'calls': [{'name': 'absent', 'return_flow': False}]}
    result = runner.evaluate_case(tmp_path, case)
    assert next(r for r in result['checks'] if r['dimension'] == 'entry_return')['outcome'] == 'positive_found'
    assert next(r for r in result['checks'] if r['dimension'] == 'call_return')['outcome'] == 'unresolved'


def test_analysis_errors_remain_in_denominator(tmp_path):
    runner = load_runner()
    case = {'id': 'invalid', 'category': 'runner', 'module': 'absent', 'entry': 'entry',
            'rationale': 'Missing entry is an error, never a successful negative.',
            'returns': {'x': True, 'y': False}}
    result = runner.evaluate_case(tmp_path, case)
    assert len(result['checks']) == 3
    assert all(row['outcome'] == 'error' for row in result['checks'])
    assert runner.summarize([result])['entry_return']['checks'] == 2


def test_manifest_rejects_duplicate_ids(tmp_path):
    runner = load_runner()
    case = {'id': 'same', 'category': 'runner', 'module': 'a', 'entry': 'e',
            'rationale': 'duplicate', 'returns': {'x': True}}
    (tmp_path / 'manifest.json').write_text(json.dumps({'version': 1, 'cases': [case, case]}))
    import pytest
    with pytest.raises(ValueError, match='Duplicate'):
        runner.load_cases(tmp_path)


def test_binding_keyword_and_receiver_are_distinct(tmp_path):
    runner = load_runner()
    (tmp_path / 'sample.py').write_text(
        'class Example:\n    def helper(self, *, x):\n        return x\n'
        '    def entry(self, x):\n        return self.helper(x=x)\n')
    case = {'id': 'slots', 'category': 'runner', 'module': 'sample', 'entry': 'Example.entry',
            'rationale': 'Exact explicit keyword and implicit receiver slots.', 'returns': {},
            'calls': [{'name': 'self.helper', 'bindings': {'kw:x': 'x', 'receiver': 'self'},
                       'receiver_flows': [['self', 'self', True], ['x', 'self', False]]}]}
    result = runner.evaluate_case(tmp_path, case)
    assert len(result['checks']) == 6
    assert all(row['outcome'] not in runner.FAILURES for row in result['checks'])


def test_default_binding_is_verified_separately(tmp_path):
    runner = load_runner()
    (tmp_path / 'sample.py').write_text(
        'def helper(x=1):\n    return x\ndef entry():\n    return helper()\n')
    case = {'id': 'default', 'category': 'runner', 'module': 'sample', 'entry': 'entry',
            'rationale': 'No explicit argument slot supplies a default.',
            'calls': [{'name': 'helper', 'bindings': {'default:x': 'x'}}]}
    result = runner.evaluate_case(tmp_path, case)
    assert result['checks'][-1]['outcome'] == 'matched'


def test_unresolved_formal_does_not_earn_negative_flow_credit(tmp_path):
    runner = load_runner()
    (tmp_path / 'sample.py').write_text('def entry(x):\n    return external(x)\n')
    case = {'id': 'unbound', 'category': 'runner', 'module': 'sample', 'entry': 'entry',
            'rationale': 'An unknown signature cannot establish absent formal flow.',
            'calls': [{'name': 'external', 'flows': [['x', 'data', False]]}]}
    result = runner.evaluate_case(tmp_path, case)
    assert result['checks'][-1]['outcome'] == 'unresolved'


def test_colon_in_callee_does_not_corrupt_binding_subject(tmp_path, monkeypatch):
    runner = load_runner()
    from pcresolve.flow import FlowAnalysis, FlowCall, FunctionRef
    entry = FunctionRef(module='sample', qualname='entry')
    call = FlowCall('call', entry, "dispatch['a:b']", 2, 11,
                    parameter_bindings=[{'argument': {'position': 0}, 'parameter': 'data', 'status': 'exact'}],
                    parameter_flows=[{'source_parameter': 'x', 'target_parameter': 'data'}])
    snapshot = FlowAnalysis(entry, {}, calls=[call])
    class Analyzer:
        def __init__(self, **kwargs):
            pass

        def analyze(self, *args, **kwargs):
            return snapshot
    monkeypatch.setattr(runner, 'FlowAnalyzer', Analyzer)
    case = {'id': 'colon', 'category': 'runner', 'module': 'sample', 'entry': 'entry', 'inventory': False,
            'rationale': 'Call syntax is opaque, not a delimiter-based data format.',
            'calls': [{'name': "dispatch['a:b']", 'bindings': {'0': 'data'},
                       'flows': [['x', 'data', True]]}]}
    assert all(row['outcome'] not in runner.FAILURES
               for row in runner.evaluate_case(tmp_path, case)['checks'])


def test_call_inventory_catches_nested_calls_sharing_start_position(tmp_path):
    runner = load_runner()
    (tmp_path / 'sample.py').write_text('def entry(x):\n    return make().convert(x)\n')
    case = {'id': 'inventory', 'category': 'runner', 'module': 'sample', 'entry': 'entry',
            'rationale': 'Inner and outer calls share start offsets but are distinct syntax nodes.'}
    result = runner.evaluate_case(tmp_path, case)
    check = next(r for r in result['checks'] if r['dimension'] == 'call_inventory')
    assert check['actual'] == (not result['diagnostic']['inventory']['missing']
                               and not result['diagnostic']['inventory']['extra'])
    assert result['diagnostic']['inventory']['expected_count'] == 2


def test_markdown_report_keeps_unresolved_checks_visible():
    runner = load_runner()
    result = {'id': 'probe', 'category': 'binding', 'rationale': 'Known formal unavailable.',
              'checks': [{'dimension': 'binding', 'subject': 'helper#0:0', 'expected': 'x',
                          'actual': None, 'outcome': 'unresolved'}]}
    report = {'case_count': 1, 'revision': 'abc123', 'python': '3.9',
              'results': [result], 'dimensions': runner.summarize([result])}
    rendered = runner.render_markdown(report)
    assert 'unresolved' in rendered and 'helper#0:0' in rendered
    assert 'abc123' in rendered and 'binding' in rendered


def test_inventory_includes_definition_time_default_calls(tmp_path):
    runner = load_runner()
    (tmp_path / 'sample.py').write_text(
        'def helper(x):\n    return x\ndef entry(x):\n'
        '    def inner(value=helper(x)):\n        return value\n    return inner()\n')
    case = {'id': 'default_calls', 'category': 'runner', 'module': 'sample', 'entry': 'entry',
            'rationale': 'Defaults run in the defining scope, nested body calls do not.'}
    result = runner.evaluate_case(tmp_path, case)
    assert result['diagnostic']['inventory']['expected_count'] == 2
    assert next(r for r in result['checks'] if r['dimension'] == 'call_inventory')['outcome'] == 'matched'
