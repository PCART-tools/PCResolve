## @package tests.test_value_flow_constructor_bindings

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from tests.flow_test_support import set_class_binding_limit
import pcresolve.flow.analyzer as flow
import pcresolve.flow.index.definitions as flow_definitions

ROOT = Path(__file__).parent / 'fixtures/value_flow_constructor_bindings'


def analyze(name, analyzer=None, **limits):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef('cases', name), max_depth=4, **limits)


@pytest.mark.parametrize('entry,callee,receiver', [
    ('direct', 'FixedNew', 'FixedNew'), ('inherited', 'DerivedNew', 'DerivedNew'),
    ('indirect', 'factory', 'FixedNew'),
    ('explicit_static', 'StaticNew', 'StaticNew'),
    ('positional', 'PositionalNew', 'PositionalNew'),
])
def test_explicit_source_constructor_binds_cls_before_entering_new(entry, callee, receiver):
    result = analyze(entry)
    call = next(c for c in result.calls if c.callee_name == callee)
    facts = getattr(call, 'constructor_bindings', [])
    assert len(facts) == 1
    fact = facts[0]
    assert fact['status'] == 'source_bound'
    assert fact['phase'] == '__new__'
    assert fact['receiver_class']['qualname'] == receiver
    assert fact['runtime_target_confirmed'] is False
    assert fact['instance_state'] == 'unmodeled'
    implicit = next(a for a in call.argument_sources if a.get('parameter') == 'cls')
    assert implicit['argument'] == {'constructor_class': True}
    assert implicit['sources'][0]['class_type']['qualname'] == receiver
    sink = next(c for c in result.calls if c.callee_name == 'cls.fixed')
    assert sink.class_method_bindings[0]['status'] == 'source_bound'
    assert sink.class_method_bindings[0]['receiver_class']['qualname'] == receiver


@pytest.mark.parametrize('entry', ['custom', 'patched', 'escaped', 'captured', 'escaped_base'])
def test_unproved_constructor_lookup_cannot_supply_an_implicit_receiver(entry):
    result = analyze(entry)
    calls = [c for c in result.calls if c.caller.qualname == entry]
    constructors = [c for c in calls if c.target_status == 'constructor']
    assert calls
    for call in constructors:
        assert not any(f.get('status') == 'source_bound'
                       for f in getattr(call, 'constructor_bindings', []))
        assert not any(a.get('argument') == {'constructor_class': True}
                       for a in call.argument_sources)
    assert any(b['reason'] == 'constructor_binding_unconfirmed' for b in result.boundaries) or (
        not constructors and any(b['reason'] in ('constructor_unavailable', 'definition_unavailable')
                                for b in result.boundaries))


def test_plain_new_query_does_not_gain_a_constructed_class_origin():
    result = analyze('FixedNew.__new__')
    sink = next(c for c in result.calls if c.callee_name == 'cls.fixed')
    assert sink.class_method_bindings[0]['status'] == 'unconfirmed'


def test_new_binding_does_not_claim_initialized_instance_or_init_phase_execution():
    result = analyze('both')
    call = next(c for c in result.calls if c.callee_name == 'Both')
    assert call.target.qualname == 'Both.__new__'
    assert call.constructor_bindings[0]['status'] == 'source_bound'
    assert call.constructor_bindings[0]['instance_state'] == 'unmodeled'
    assert not any(c.caller.qualname == 'Both.__init__' for c in result.calls)
    assert any(b['reason'] == 'constructor_initialization_unmodeled'
               for b in result.boundaries)


def test_new_binding_respects_expansion_snapshots_and_function_budgets():
    analyzer = FlowAnalyzer(project_root=ROOT)
    initial = analyzer.analyze(FunctionRef('cases', 'direct'))
    before = initial.to_dict()
    call = next(c for c in initial.calls if c.callee_name == 'FixedNew')
    expanded = analyzer.expand(initial, call.id)
    assert any(c.callee_name == 'cls.fixed' and c.class_method_bindings[0]['status']
               == 'source_bound' for c in expanded.calls)
    assert initial.to_dict() == before
    bounded = analyze('direct', max_functions=1)
    assert any(b['reason'] == 'budget_exceeded' for b in bounded.boundaries)
    assert not any(c.callee_name == 'cls.fixed' for c in bounded.calls)


@pytest.mark.parametrize('entry', ['collision', 'expanded_collision'])
def test_explicit_keyword_cannot_rebind_the_implicit_positional_class(entry):
    result = analyze(entry)
    call = next(c for c in result.calls if c.callee_name == 'FixedNew')
    assert call.binding_status == 'invalid'
    assert any(issue['kind'] == 'duplicate_binding' and issue['parameter'] == 'cls'
               for issue in call.binding_issues)


def test_positional_only_class_parameter_allows_same_named_keyword_in_kwargs():
    result = analyze('positional_only')
    call = next(c for c in result.calls if c.callee_name == 'PosOnlyNew')
    assert call.binding_status != 'invalid'
    assert call.constructor_bindings[0]['status'] == 'source_bound'
    cls_values = next(a for a in call.argument_sources if a['argument']
                      == {'constructor_class': True})
    assert cls_values['sources'][0]['class_type']['qualname'] == 'PosOnlyNew'


def test_argument_evaluation_can_invalidate_the_saved_constructor_object_lookup():
    result = analyze('argument_escape')
    call = next(c for c in result.calls if c.callee_name == 'FixedNew')
    assert call.constructor_bindings[0]['status'] == 'unconfirmed'


def test_constructor_controls_agree_with_python_call_order_and_implicit_arguments():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for entry in ('direct', 'inherited', 'indirect', 'explicit_static'):
        assert values[entry](allowed=1) == 1
        with pytest.raises(TypeError, match='unexpected keyword argument'):
            values[entry](old=1)
    for entry in ('collision', 'expanded_collision'):
        with pytest.raises(TypeError, match='multiple values for argument'):
            values[entry](old=1)
    assert values['custom'](old=1) == {'old': 1}
    assert values['positional_only'](old=1) == {'cls': 1, 'old': 1}
    assert values['both'](old=1) == 1
    assert values['positional'](1) == 1
    with pytest.raises(TypeError, match='positional arguments'):
        values['positional'](1, 2)
    with pytest.raises(TypeError, match='keywords must be strings'):
        values['invalid_keys'](old=1)


def test_definitely_invalid_expansion_cannot_license_a_normal_allocator_body():
    result = analyze('invalid_keys')
    call = next(c for c in result.calls if c.callee_name == 'FixedNew')
    assert call.constructor_bindings[0]['status'] == 'unconfirmed'
    assert any(issue['reason'] == 'constructor_expansion_unconfirmed'
               for issue in call.constructor_bindings[0]['issues'])


def test_bound_allocator_can_have_a_deferred_body_without_initialized_instance_state():
    result = analyze('deferred')
    call = next(c for c in result.calls if c.callee_name == 'DeferredNew')
    fact = call.constructor_bindings[0]
    assert fact['status'] == 'source_bound'
    assert fact['body_execution'] == 'deferred'
    assert fact['instance_state'] == 'unmodeled'


def test_constructor_proof_budget_and_receiver_query_order_do_not_contaminate_a_snapshot(monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyze('direct', analyzer)
    before = first.to_dict()
    analyze('custom', analyzer)
    analyze('inherited', analyzer)
    assert analyze('direct', analyzer).to_dict() == before
    with monkeypatch.context() as patch:
        set_class_binding_limit(patch, 1)
        limited = analyze('direct', analyzer)
        call = next(c for c in limited.calls if c.callee_name == 'FixedNew')
        assert call.constructor_bindings[0]['status'] == 'unconfirmed'
        assert any(issue['reason'] == 'constructor_binding_budget'
                   for issue in call.constructor_bindings[0]['issues'])
    assert analyze('direct', analyzer).to_dict() == before
    assert first.to_dict() == before


@pytest.mark.parametrize('entry,selected', [
    ('skips_init', 'SkipsInit.__new__'),
    ('inherited_skip', 'SkipsInit.__new__'),
    ('inherited_new', 'FixedNew.__new__'),
    ('fixed_allocator', 'FixedAllocator.__new__'),
    ('ordinary_init', 'OrdinaryInit.__init__'),
    ('inherited_init', 'OrdinaryInit.__init__'),
])
def test_constructor_selection_observes_allocator_before_initializer(entry, selected):
    result = analyze(entry)
    call = next(c for c in result.calls if c.caller.qualname == entry)
    assert call.target.qualname == selected
    assert not any(c.caller.qualname in ('SkipsInit.__init__', 'InheritedSkip.__init__',
        'Allocates.__init__', 'FixedAllocator.__init__') for c in result.calls)


@pytest.mark.parametrize('entry', ['custom_init', 'assigned_new', 'rebound_new',
                                 'inherited_rebound', 'hooked_init'])
def test_unproven_allocation_cannot_select_an_initializer(entry):
    result = analyze(entry)
    call = next(c for c in result.calls if c.caller.qualname == entry)
    assert call.target is None
    assert any(b['reason'] in ('constructor_unavailable', 'definition_unavailable')
               for b in result.boundaries)


def test_python_skips_initialization_after_an_allocator_returns_a_non_instance():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for entry in ('skips_init', 'inherited_skip', 'assigned_new', 'rebound_new',
                  'inherited_rebound', 'hooked_init'):
        assert values[entry](old=1) == 1
    assert values['inherited_new'](allowed=1) == 1
    assert values['fixed_allocator'](allowed=1) == 1
    assert values['custom_init'](old=1) == {'old': 1}
    for entry in ('inherited_new', 'fixed_allocator', 'ordinary_init', 'inherited_init'):
        with pytest.raises(TypeError, match='unexpected keyword argument'):
            values[entry](old=1)


def test_source_allocation_does_not_yet_establish_later_initializer_execution():
    result = analyze('needs_init')
    call = next(c for c in result.calls if c.callee_name == 'NeedsInit')
    assert call.target.qualname == 'NeedsInit.__new__'
    assert call.constructor_bindings[0]['execution_scope'] == 'new_invocation_only'
    assert any(b['reason'] == 'constructor_initialization_unmodeled'
               and b['phase'] == '__init__' for b in result.boundaries)
    values = runpy.run_path(str(ROOT / 'cases.py'))
    assert values['needs_init'](allowed=1).allowed == 1
    with pytest.raises(TypeError, match='unexpected keyword argument'):
        values['needs_init'](old=1)


def test_initializer_selection_budget_is_unknown_rather_than_no_flow(monkeypatch):
    set_class_binding_limit(monkeypatch, 1)
    result = analyze('ordinary_init')
    call = next(c for c in result.calls if c.callee_name == 'OrdinaryInit')
    assert call.target is None
    assert any(b['reason'] == 'constructor_binding_budget' for b in result.boundaries)


def test_descriptor_classification_cannot_erase_the_constructor_phase():
    result = analyze('custom_descriptor')
    call = next(c for c in result.calls if c.callee_name == 'CustomDescriptorNew')
    assert call.target_status == 'constructor'
    assert call.constructor_bindings[0]['status'] == 'unconfirmed'
    assert any(issue['reason'] == 'constructor_new_descriptor_unconfirmed'
               for issue in call.constructor_bindings[0]['issues'])
    values = runpy.run_path(str(ROOT / 'cases.py'))
    with pytest.raises(TypeError, match='positional argument'):
        values['custom_descriptor'](old=1)
