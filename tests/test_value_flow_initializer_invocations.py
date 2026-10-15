## @package tests.test_value_flow_initializer_invocations

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_initializer_invocations'


@pytest.mark.parametrize('name,cls,target', [
    ('construct_open', 'Open', 'Open.fixed'),
    ('construct_fixed', 'Fixed', 'Fixed.fixed'),
    ('construct_inherited', 'Inherited', 'Base.fixed'),
    ('construct_alias', 'AliasOpen', 'AliasOpen.fixed'),
])
def test_ordinary_constructor_binds_its_actual_uninitialized_instance(name, cls, target):
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef('cases', name))
    call = next(c for c in result.calls if c.target_status == 'constructor')
    fact = call.constructor_bindings[0]
    assert fact['status'] == 'source_bound'
    assert fact['phase'] == '__init__'
    assert fact['execution_scope'] == 'init_invocation_only'
    assert fact['receiver_class']['qualname'] == cls
    assert fact['instance_state'] == 'unmodeled'
    assert fact['runtime_target_confirmed'] is False
    receiver = call.argument_sources[0]
    assert receiver['argument'] == {'constructor_instance': True}
    assert receiver['sources'][0]['instance_type']['qualname'] == cls
    snapshot = result.to_dict()
    expanded = analyzer.expand(result, call.id)
    inner = next(c for c in expanded.calls if c.callee_name in ('self.fixed', 'alias.fixed'))
    assert inner.target.qualname == target
    assert inner.analysis_contexts[0]['incoming_call_id'] == call.id
    assert result.to_dict() == snapshot


@pytest.mark.parametrize('name', ['construct_shadowed', 'construct_escaped', 'construct_lookup'])
def test_unproven_instance_lookup_cannot_become_a_nominal_base_method(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=2)
    call = result.find_calls(callee_name='self.fixed')[0]
    assert call.target is None


def test_initializer_implicit_receiver_conflicts_with_an_explicit_keyword():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'collision'))
    call = result.find_calls(callee_name='Open')[0]
    assert call.binding_status == 'invalid'
    assert any(issue['kind'] == 'duplicate_binding' and issue['parameter'] == 'self'
               for issue in call.binding_issues)


def test_positional_only_receiver_does_not_conflict_with_a_keyword_in_kwargs():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'posonly_keyword'))
    call = result.find_calls(callee_name='AliasOpen')[0]
    assert call.binding_status != 'invalid'
    assert call.constructor_bindings[0]['status'] == 'source_bound'
    assert any(binding.get('argument') == {'keyword': 'this'}
               and binding['parameter'] == 'kwargs' for binding in call.parameter_bindings)


def test_argument_effects_can_invalidate_the_selected_constructor_binding():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'argument_escape'))
    call = result.find_calls(callee_name='Open')[0]
    assert call.constructor_bindings[0]['status'] == 'unconfirmed'


def test_runtime_open_override_and_custom_lookup_accept_the_old_keyword():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ('construct_open', 'construct_alias', 'construct_lookup', 'posonly_keyword'):
        assert values[name](old=1) is not None
    with pytest.raises(TypeError, match='unexpected keyword argument'):
        values['construct_fixed'](old=1)


def test_unknown_escape_can_really_replace_the_instance_method():
    values = runpy.run_path(str(ROOT / 'cases.py'))

    def replace(receiver):
        receiver.fixed = lambda **kwargs: kwargs

    values['construct_escaped'].__globals__['external'] = replace
    assert values['construct_escaped'](old=1) is not None
