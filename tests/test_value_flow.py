from pathlib import Path
import json

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def analyze(name='entry', files=None):
    analyzer = FlowAnalyzer(source_files=files or list(ROOT.glob('*.py')),
                            import_roots=[ROOT])
    return analyzer, analyzer.analyze(FunctionRef(module='main', qualname=name))


def test_branch_parameter_and_return_flow():
    _, result = analyze()
    call = result.find_calls(callee_name='convert')[0]
    details = result.describe_call_flow(call.id)
    assert call.target.qualname == 'convert'
    assert details['parameter_bindings'][0]['parameter'] == 'data'
    assert {f['source_parameter'] for f in details['parameter_flows']} == {'arg', 'errors'}
    assert {f['relation'] for f in details['parameter_flows'] if f['source_parameter'] == 'arg'} == {'direct', 'derived'}
    assert details['return_flows']
    assert any('return result' in e['source_text'] for e in details['return_flows'][0]['evidence'])
    json.dumps(result.to_dict())


def test_discarded_result_and_distinct_calls():
    _, result = analyze('discarded')
    assert not result.describe_call_flow(result.calls[0].id)['return_flows']
    _, result = analyze('repeated')
    assert len({c.id for c in result.calls}) == 2
    assert not result.describe_call_flow(result.calls[0].id)['return_flows']
    assert result.describe_call_flow(result.calls[1].id)['return_flows']


def test_missing_definition_then_expand_and_add_files():
    analyzer, first = analyze(files=[ROOT / 'main.py'])
    assert first.calls[0].target is None
    assert first.describe_call_flow(first.calls[0].id)['parameter_flows']
    analyzer.add_files([ROOT / 'helper.py'])
    second = analyzer.analyze(first.entry)
    expanded = analyzer.expand(second, second.calls[0].id, additional_depth=1)
    assert len(expanded.functions) == 2
    assert len(second.functions) == 1
    assert len(first.inputs['source_files']) == 1


def test_project_input_and_depth_budget():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef(module='main', qualname='entry'), max_depth=2)
    assert len(result.functions) == 2
    limited = analyzer.analyze(result.entry, max_depth=2, max_functions=1)
    assert any(b['reason'] == 'budget_exceeded' for b in limited.boundaries)


def test_cross_call_parameter_to_return_is_composed_only_after_expansion():
    analyzer, result = analyze('through')
    assert not result.trace_parameter('x')['return_paths']
    expanded = analyzer.expand(result, result.calls[0].id)
    paths = expanded.trace_parameter('x')['return_paths']
    assert len(paths) == 1
    assert paths[0]['call_context'] == [result.calls[0].id]


def test_rebound_callable_is_not_resolved_to_import():
    _, result = analyze('rebound')
    assert result.calls[0].target is None


def test_nested_call_contexts_and_default_binding():
    analyzer, result = analyze('nested')
    expanded = analyzer.analyze(result.entry, max_depth=2)
    paths = expanded.trace_parameter('x')['return_paths']
    assert len(paths) == 1
    assert len(paths[0]['call_context']) == 2
    assert any(b.get('binding_kind') == 'default' for b in expanded.calls[0].parameter_bindings)


def test_call_budget_is_a_hard_bound():
    analyzer, result = analyze('repeated')
    limited = analyzer.analyze(result.entry, max_call_contexts=1)
    assert len(limited.calls) <= 1
    assert any(b['reason'] == 'budget_exceeded' for b in limited.boundaries)


def test_expanding_existing_summary_deeper_matches_one_shot():
    analyzer, initial = analyze('deep')
    once = analyzer.expand(initial, initial.calls[0].id, additional_depth=1)
    twice = analyzer.expand(once, initial.calls[0].id, additional_depth=2)
    full = analyzer.analyze(initial.entry, max_depth=3)
    assert len(twice.functions) == len(full.functions) == 3
    assert twice.trace_parameter('x')['return_paths'] == full.trace_parameter('x')['return_paths']
