from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_matrix' / 'binding'
EDGE_ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(entry):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=3)


def test_varargs_and_kwargs_keep_formal_element_paths():
    positional = run('variadic_argument')
    assert not positional.trace_parameter('x')['return_paths']
    assert positional.trace_parameter('y')['return_paths']
    call = positional.find_calls(callee_name='variadic')[0]
    assert [a.get('target_path') for a in call.argument_sources
            if a['parameter'] == 'rest'] == [[0], [1]]

    keywords = run('variadic_keyword')
    assert not keywords.trace_parameter('x')['return_paths']
    assert keywords.trace_parameter('y')['return_paths']
    call = keywords.find_calls(callee_name='keyword_variadic')[0]
    assert {tuple(a.get('target_path', [])) for a in call.argument_sources
            if a['parameter'] == 'values'} == {('left',), ('right',)}


def test_known_star_expansion_binds_each_formal():
    result = run('literal_star')
    call = result.find_calls(callee_name='positional')[0]
    edges = {(flow['source_parameter'], flow['target_parameter'])
             for flow in call.parameter_flows}
    assert ('x', 'first') in edges
    assert ('y', 'second') in edges
    assert not result.trace_parameter('x')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_unknown_star_does_not_block_explicit_keyword_binding():
    result = run('star_and_keyword')
    call = result.find_calls(callee_name='after_star')[0]
    binding = next(b for b in call.parameter_bindings
                   if b['argument'] == {'keyword': 'result'})
    assert binding['parameter'] == 'result'
    assert binding['status'] == 'exact'
    assert not result.trace_parameter('items')['return_paths']
    assert result.trace_parameter('y')['return_paths']


def test_positional_only_parameter_rejects_keyword_binding():
    result = FlowAnalyzer(project_root=EDGE_ROOT).analyze(
        FunctionRef(module='binding_edge_cases', qualname='invalid_positional_keyword'),
        max_depth=2)
    call = result.find_calls(callee_name='positional_only')[0]
    assert call.parameter_bindings[0]['parameter'] is None
    assert call.parameter_bindings[0]['status'] == 'unresolved'
    assert not call.return_flows
    assert any(boundary.get('reason') == 'invalid_argument_binding'
               for boundary in result.boundaries)


def test_decorator_replacement_with_capture_remains_unresolved():
    result = FlowAnalyzer(project_root=EDGE_ROOT).analyze(
        FunctionRef(module='binding_edge_cases', qualname='call_captured_replacement'),
        max_depth=2)
    assert result.find_calls(callee_name='captured_replacement')[0].target is None
