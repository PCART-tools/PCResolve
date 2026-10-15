## @package tests.test_value_flow_instance_edges

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_instance_edges'


@pytest.mark.parametrize('name,callee,target', [
    ('Open', 'self.fixed', 'Open.fixed'), ('Fixed', 'self.fixed', 'Fixed.fixed'),
    ('construct_open', 'self.fixed', 'Open.fixed'),
    ('construct_fixed', 'self.fixed', 'Fixed.fixed'),
    ('HelperOpen', 'receiver.fixed', 'HelperOpen.fixed'),
    ('HelperFixed', 'receiver.fixed', 'HelperFixed.fixed'),
])
def test_source_instance_survives_exact_method_and_ordinary_helper_edges(name, callee, target):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=4)
    call = result.find_calls(callee_name=callee)[0]
    assert call.target.qualname == target
    assert call.analysis_contexts
    assert all(context['parameter_facts'] for context in call.analysis_contexts)


def test_plain_method_receiver_has_an_exact_implicit_binding():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Open'))
    call = result.find_calls(callee_name='self.forward')[0]
    assert {'argument': {'receiver': True}, 'parameter': 'self', 'status': 'exact',
            'binding_kind': 'implicit_receiver', 'destination_kind': 'parameter'} in call.parameter_bindings


def test_bound_receiver_keyword_collision_prevents_the_method_body():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Collision'), max_depth=3)
    call = result.find_calls(callee_name='self.forward')[0]
    assert call.binding_status == 'invalid'
    assert any(issue['kind'] == 'duplicate_binding' and issue['parameter'] == 'self'
               for issue in call.binding_issues)
    assert all(not value.get('instance_type')
               for inner in result.find_calls(callee_name='self.fixed')
               for value in inner.receiver_sources)


def test_positional_only_receiver_keyword_stays_in_variadic_arguments():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'PosOnly'), max_depth=3)
    call = result.find_calls(callee_name='this.forward')[0]
    assert call.binding_status != 'invalid'
    assert result.find_calls(callee_name='this.fixed')[0].target.qualname == 'PosOnly.fixed'


def test_exposed_receiver_does_not_acquire_an_exact_downstream_type():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Escapes'), max_depth=3)
    assert result.find_calls(callee_name='self.forward')[0].target is None


def test_argument_escape_preserves_the_selected_method_but_invalidates_its_body_receiver():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'ArgumentEscape'), max_depth=3)
    call = result.find_calls(callee_name='self.forward')[0]
    assert call.target.qualname == 'Base.forward'
    assert result.find_calls(callee_name='self.fixed')[0].target is None


def test_runtime_open_and_fixed_helper_paths_are_distinct():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ('Open', 'HelperOpen', 'PosOnly'):
        assert values[name](old=1) is not None
    for name in ('Fixed', 'HelperFixed', 'Collision'):
        with pytest.raises(TypeError):
            values[name](old=1)


def test_unknown_argument_effect_can_change_dispatch_inside_the_selected_method():
    values = runpy.run_path(str(ROOT / 'cases.py'))

    class Replacement:
        def fixed(self, **kwargs):
            return kwargs

    def replace(receiver):
        receiver.__class__ = Replacement

    values['ArgumentEscape'].__init__.__globals__['external'] = replace
    assert isinstance(values['ArgumentEscape'](old=1), Replacement)


def test_generic_helper_parameters_do_not_acquire_an_instance_type():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'relay'))
    assert result.find_calls(callee_name='receiver.fixed')[0].target is None
