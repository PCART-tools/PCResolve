from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_matrix' / 'binding'


def run(entry):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=3)


def test_builtin_staticmethod_and_classmethod_binding():
    static = run('static_descriptor')
    assert static.trace_parameter('x')['return_paths']
    static_call = static.find_calls(callee_name='Descriptors.static_echo')[0]
    assert static_call.target.qualname == 'Descriptors.static_echo'
    assert static_call.parameter_bindings[0]['parameter'] == 'data'

    classed = run('class_descriptor')
    assert classed.trace_parameter('x')['return_paths']
    class_call = classed.find_calls(callee_name='Descriptors.class_echo')[0]
    assert class_call.target.qualname == 'Descriptors.class_echo'
    receiver = next(binding for binding in class_call.argument_sources
                    if binding['argument'] == {'receiver': True})
    assert receiver['parameter'] == 'cls'
    assert not receiver['sources']
    assert class_call.parameter_bindings[0]['parameter'] == 'data'


def test_zero_argument_super_binds_current_instance_to_parent_method():
    result = run('ParentDispatch.via_super')
    assert not result.trace_parameter('self')['return_paths']
    assert result.trace_parameter('x')['return_paths']
    call = result.find_calls(callee_name='super().echo')[0]
    assert call.target.qualname == 'Base.echo'
    receiver = next(binding for binding in call.argument_sources
                    if binding['argument'] == {'receiver': True})
    assert receiver['parameter'] == 'self'
    assert {source['source'] for source in receiver['sources']} == {'self'}
    assert call.parameter_bindings[0]['parameter'] == 'data'
