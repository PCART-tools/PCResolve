from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_matrix' / 'containers'
EDGE_ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(entry):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=3)


def test_dictionary_keys_and_overwrites_keep_precise_paths():
    returned = run('returned_dictionary')
    assert returned.trace_parameter('key')['return_paths']
    assert returned.trace_parameter('value')['return_paths']

    dynamic = run('overwritten_dynamic_key')
    assert not dynamic.trace_parameter('x')['return_paths']
    assert dynamic.trace_parameter('y')['return_paths']

    unpacked = run('unpacked_dictionary_overwrite')
    assert not unpacked.trace_parameter('x')['return_paths']
    assert unpacked.trace_parameter('y')['return_paths']


def test_mutating_protocol_calls_preserve_their_result_endpoint():
    appended = run('append_result')
    assert not appended.trace_parameter('x')['return_paths']
    assert appended.find_calls(callee_name='values.append')[0].return_flows

    popped = run('popped_element')
    assert popped.trace_parameter('x')['return_paths']
    assert not popped.trace_parameter('y')['return_paths']
    assert popped.find_calls(callee_name='values.pop')[0].return_flows


def test_pop_normalizes_default_and_negative_indices():
    analyzer = FlowAnalyzer(project_root=EDGE_ROOT)
    last = analyzer.analyze(FunctionRef(module='container_edges', qualname='pop_last'))
    assert not last.trace_parameter('x')['return_paths']
    assert last.trace_parameter('y')['return_paths']

    negative = analyzer.analyze(FunctionRef(module='container_edges', qualname='pop_negative'))
    assert negative.trace_parameter('y')['return_paths']
    assert not negative.trace_parameter('x')['return_paths']
    assert not negative.trace_parameter('z')['return_paths']

    invalid = analyzer.analyze(FunctionRef(
        module='container_edges', qualname='pop_out_of_range'))
    assert not invalid.trace_parameter('x')['return_paths']
    assert not invalid.find_calls(callee_name='values.pop')[0].return_flows
