## @package tests.test_value_flow_explicit_allocation

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_explicit_allocation'


def analyze(entry):
    return FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', entry), max_depth=4)


def test_direct_object_allocation_bypasses_the_class_custom_new():
    result = analyze('bypass')
    call = result.find_calls(callee_name='instance.initialize')[0]
    assert call.target.qualname == 'Backend.initialize'
    assert call.receiver_sources[0]['instance_type']['qualname'] == 'Backend'
    assert analyze('ordinary').find_calls(callee_name='instance.initialize')[0].target is None


def test_super_allocation_keeps_closed_alternatives_without_selecting_one():
    call = analyze('Factory.mixed').find_calls(callee_name='instance.initialize')[0]
    assert call.target is None and call.target_status == 'bounded_alternatives'
    assert {value['qualname'] for value in call.target_candidates} == {'Backend.initialize', 'Other.initialize'}


@pytest.mark.parametrize('entry', ['Factory.shadowed', 'rebound', 'CustomFactory.allocate',
                                 'unknown', 'definition_effects', 'AssignedFactory.allocate',
                                 'PatchedFactory.allocate'])
def test_unproved_allocator_and_class_state_never_become_builtin_instances(entry):
    call = analyze(entry).find_calls(callee_name='instance.initialize')[0]
    assert call.target is None and not call.target_candidates


def test_allocation_candidates_are_query_local_and_budgeted():
    analyzer = FlowAnalyzer(project_root=ROOT)
    ref = FunctionRef('cases', 'Factory.conditional')
    snapshot = analyzer.analyze(ref, max_depth=4).to_dict()
    analyzer.analyze(FunctionRef('cases', 'ordinary'), max_depth=4)
    assert analyzer.analyze(ref, max_depth=4).to_dict() == snapshot
    result = analyzer.analyze(ref, max_depth=4, max_functions=1, max_call_contexts=1)
    assert any('budget' in boundary['reason'] for boundary in result.boundaries)


def test_runtime_explicit_allocator_bypasses_new_but_configuration_remains_mutable():
    values = runpy.run_path(str(ROOT / 'cases.py'), init_globals={
        'external_base': object, 'unknown_factory': lambda: None})
    assert values['Backend']() == 'replaced'
    assert values['bypass'](allowed=9) == 9
    with pytest.raises(AttributeError, match='initialize'):
        values['ordinary'](allowed=9)
    assert values['Factory'].conditional(allowed=7) == 7
    values['Factory'].implementation = values['Other']
    assert values['Factory'].conditional(other=8) == 8
