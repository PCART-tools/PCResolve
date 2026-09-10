import importlib.util
from pathlib import Path


def test_evaluation_keeps_failures_and_unknowns_visible():
    path = Path(__file__).resolve().parents[1] / 'scripts' / 'evaluate_value_flow.py'
    spec = importlib.util.spec_from_file_location('flow_evaluation', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.evaluate()
    assert report['case_count'] == 12
    assert report['dimensions']['entry_return']['expected_positive'] > 0
    assert report['dimensions']['entry_return']['expected_negative'] > 0
    assert report['dimensions']['entry_return']['negative_no_path'] > 0
    assert len(report['results']) == sum(
        v['checks'] for v in report['dimensions'].values())


def test_independent_probe_regressions():
    from pcresolve import FlowAnalyzer, FunctionRef
    import json
    root = Path(__file__).parent / 'fixtures' / 'value_flow_eval'
    manifest = json.loads((root / 'expected.json').read_text())
    failures = []
    for case in manifest['cases']:
        result = FlowAnalyzer(project_root=root).analyze(
            FunctionRef(module='cases', qualname=case['entry']), max_depth=3)
        for parameter, expected in case['returns'].items():
            if bool(result.trace_parameter(parameter)['return_paths']) != expected:
                failures.append((case['entry'], parameter))
    assert not failures
def test_generalization_counterexamples():
    from pcresolve import FlowAnalyzer, FunctionRef
    root = Path(__file__).parent / 'fixtures' / 'value_flow_eval'
    expected = {'reverse_selection': {'x': False, 'y': True},
                'out_of_bounds': {'x': False}, 'appended_index': {'y': True},
                'comprehension_constant': {'x': False},
                'comprehension_scope': {'x': False, 'y': True},
                'nested_clear': {'x': False}, 'rebound_container': {'x': False},
                'Shadowed.run': {'x': False}, 'empty_comprehension': {'x': False},
                'rejected_comprehension': {'x': False}, 'unawaited_mutation': {'x': False}}
    for name, parameters in expected.items():
        result = FlowAnalyzer(project_root=root).analyze(
            FunctionRef(module='cases', qualname=name), max_depth=3)
        for parameter, positive in parameters.items():
            assert bool(result.trace_parameter(parameter)['return_paths']) == positive, (name, parameter)
