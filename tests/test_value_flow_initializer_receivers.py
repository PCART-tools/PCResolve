## @package tests.test_value_flow_initializer_receivers

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_initializer_receivers'


@pytest.mark.parametrize('name,callee,target', [
    ('Base', 'self.fixed', 'Base.fixed'),
    ('Open', 'self.fixed', 'Open.fixed'),
    ('Fixed', 'self.fixed', 'Fixed.fixed'),
    ('Inherited', 'self.fixed', 'Base.fixed'),
    ('AliasOpen', 'alias.fixed', 'AliasOpen.fixed'),
])
def test_initializer_lookup_prefers_its_actual_instance_to_the_lexical_owner(name, callee, target):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    call = result.find_calls(callee_name=callee)[0]
    assert result.inputs['entry_binding']['receiver_class']['qualname'] == name
    assert call.target.qualname == target
    assert all(value['instance_type']['qualname'] == name for value in call.receiver_sources)


@pytest.mark.parametrize('name', ['Shadowed', 'Changed'])
def test_unknown_or_modified_actual_receiver_does_not_recover_a_lexical_target(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    call = result.find_calls(callee_name='self.fixed')[0]
    assert call.target is None
    assert call.target_status == 'receiver_unresolved'


def test_actual_class_and_nominal_method_queries_keep_independent_receiver_contexts():
    analyzer = FlowAnalyzer(project_root=ROOT)
    actual = analyzer.analyze(FunctionRef('cases', 'Open'))
    snapshot = actual.to_dict()
    generic = analyzer.analyze(FunctionRef('cases', 'Base.__init__'))
    assert generic.find_calls(callee_name='self.fixed')[0].target.qualname == 'Base.fixed'
    analyzer.analyze(FunctionRef('cases', 'Fixed'))
    assert analyzer.analyze(FunctionRef('cases', 'Open')).to_dict() == snapshot
    assert actual.to_dict() == snapshot


@pytest.mark.parametrize('mode', ['alternatives', 'empty', 'incomplete'])
def test_incoming_instance_alternatives_cannot_become_a_nominal_fixed_method(mode, monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    identities = [analyzer.analyze(FunctionRef('cases', name)).inputs[
        'entry_binding']['receiver_class'] for name in ('Open', 'Fixed')]
    facts = ({'instance_candidates': identities} if mode == 'alternatives' else
             {'instance_candidates': []} if mode == 'empty' else
             {'instance_type': identities[0], 'value_incomplete': True})
    monkeypatch.setattr(analyzer, '_incoming_facts', lambda definition, edge: {'self': [facts]})
    result = analyzer.analyze(FunctionRef('cases', 'Base.__init__'))
    call = result.find_calls(callee_name='self.fixed')[0]
    assert call.target is None
    assert {target['qualname'] for target in call.target_candidates} == (
        {'Open.fixed', 'Fixed.fixed'} if mode == 'alternatives' else set())


@pytest.mark.parametrize('name', ['Open', 'AliasOpen'])
def test_open_override_accepts_the_runtime_counterexample(name):
    values = runpy.run_path(str(ROOT / 'cases.py'))
    assert isinstance(values[name](old=1), values[name])


@pytest.mark.parametrize('name', ['Base', 'Fixed', 'Inherited'])
def test_fixed_override_rejects_the_runtime_counterexample(name):
    values = runpy.run_path(str(ROOT / 'cases.py'))
    with pytest.raises(TypeError, match='unexpected keyword argument'):
        values[name](old=1)
