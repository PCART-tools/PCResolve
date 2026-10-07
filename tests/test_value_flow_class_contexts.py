## @package tests.test_value_flow_class_contexts

import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_class_contexts'


def analyze(qualname, analyzer=None, **limits):
    analyzer = analyzer or FlowAnalyzer(project_root=ROOT)
    return analyzer.analyze(
        FunctionRef(module='hierarchy', qualname=qualname),
        max_depth=limits.pop('max_depth', 6), **limits)


def targets(result, callee, caller=None):
    found = set()
    for call in result.find_calls(callee_name=callee):
        if caller is not None and call.caller.qualname != caller:
            continue
        if call.target is not None:
            found.add((call.target.module, call.target.qualname))
        found.update((candidate['module'], candidate['qualname'])
                     for candidate in call.target_candidates)
    return found


@pytest.mark.parametrize('entry,default,backend', [
    ('Derived.root', 'Derived.default', 'DerivedBackend'),
    ('Other.root', 'Other.default', 'OtherBackend'),
    ('Base.allocate', 'Base.default', 'BaseBackend')])
def test_class_return_propagates_through_inherited_helper_to_construction(entry, default, backend):
    result = analyze(entry)
    assert targets(result, 'cls.default', 'Base.allocate') == {
        ('hierarchy', default)}
    assert targets(result, 'implementation', 'Base.allocate') == {
        ('backends', backend + '.__init__')}
    assert targets(result, 'instance.initialize', 'Base.allocate') == {
        ('backends', backend + '.initialize')}
    call = result.find_calls(callee_name='instance.initialize')[0]
    assert any(source['source'] == 'kwargs'
               for argument in call.argument_sources
               for source in argument['sources'])
    json.dumps(result.to_dict())


def test_two_subclasses_retain_bounded_targets_at_the_same_helper_callsite():
    result = analyze('both')
    assert targets(result, 'cls.default', 'Base.allocate') == {
        ('hierarchy', 'Derived.default'), ('hierarchy', 'Other.default')}
    assert targets(result, 'implementation', 'Base.allocate') == {
        ('backends', 'DerivedBackend.__init__'),
        ('backends', 'OtherBackend.__init__')}
    assert targets(result, 'instance.initialize', 'Base.allocate') == {
        ('backends', 'DerivedBackend.initialize'),
        ('backends', 'OtherBackend.initialize')}
    calls = [call for call in result.find_calls(callee_name='cls.default')
             if call.caller.qualname == 'Base.allocate']
    if len(calls) == 1:
        assert calls[0].target is None


def test_repeated_analysis_and_expand_keep_receiver_contexts_isolated():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyze('Derived.root', analyzer)
    first_facts = first.to_dict()
    other = analyze('Other.root', analyzer)
    generic = analyze('Base.allocate', analyzer)
    repeated = analyze('Derived.root', analyzer)
    assert targets(first, 'cls.default', 'Base.allocate') == {
        ('hierarchy', 'Derived.default')}
    assert targets(other, 'cls.default', 'Base.allocate') == {
        ('hierarchy', 'Other.default')}
    assert targets(generic, 'cls.default', 'Base.allocate') == {
        ('hierarchy', 'Base.default')}
    assert first.to_dict() == first_facts
    assert targets(repeated, 'instance.initialize') == targets(first, 'instance.initialize')

    initial = analyze('Derived.root', analyzer, max_depth=1)
    saved = initial.to_dict()
    selected = initial.find_calls(callee_name='super(Derived, cls).allocate')[0]
    assert selected.target is not None
    expanded = analyzer.expand(initial, selected.id, additional_depth=5)
    assert initial.to_dict() == saved
    assert targets(expanded, 'cls.default', 'Base.allocate') == {
        ('hierarchy', 'Derived.default')}
    assert targets(expanded, 'instance.initialize') == targets(first, 'instance.initialize')


def test_unknown_class_receiver_is_not_filled_from_available_subclasses():
    result = analyze('unknown_receiver')
    call = result.find_calls(callee_name='cls.allocate')[0]
    assert call.target is None
    assert call.target_candidates == []
    assert any(boundary.get('call_id') == call.id
               and boundary['reason'] == 'receiver_unresolved'
               for boundary in result.boundaries)


def test_unknown_default_return_does_not_fall_back_to_the_base_backend():
    result = analyze('UnknownBackend.root')
    assert targets(result, 'cls.default', 'Base.allocate') == {
        ('hierarchy', 'UnknownBackend.default')}
    assert targets(result, 'implementation', 'Base.allocate') == set()
    assert targets(result, 'instance.initialize', 'Base.allocate') == set()
    assert any(boundary['reason'] in ('definition_unavailable', 'receiver_unresolved')
               for boundary in result.boundaries)


def test_mixed_known_and_unknown_class_return_does_not_report_a_unique_target():
    result = analyze('partial_root')
    construction = result.find_calls(callee_name='implementation')[0]
    initialize = result.find_calls(callee_name='instance.initialize')[0]
    assert construction.target is None
    assert initialize.target is None
    assert any(boundary.get('call_id') in (construction.id, initialize.id)
               for boundary in result.boundaries)


def test_recursive_class_return_stays_bounded_and_unresolved():
    result = analyze('Recursive.root')
    assert targets(result, 'cls.default', 'Base.allocate') == {
        ('hierarchy', 'Recursive.default')}
    assert not targets(result, 'implementation', 'Base.allocate')
    assert not targets(result, 'instance.initialize', 'Base.allocate')
    assert any(boundary['reason'] in ('recursion', 'budget_exceeded', 'depth_limit')
               for boundary in result.boundaries)


def test_class_context_resolution_obeys_existing_call_budget():
    result = analyze('Derived.root', max_call_contexts=1)
    assert len(result.calls) <= 1
    assert not targets(result, 'instance.initialize')
    assert any(boundary['reason'] == 'budget_exceeded'
               for boundary in result.boundaries)


@pytest.mark.parametrize('entry', ['known_then_unknown', 'unknown_then_known'])
def test_unknown_receiver_context_does_not_reuse_a_known_helper_summary(entry):
    result = analyze(entry)
    assert targets(result, 'cls.default', 'Base.allocate') == {
        ('hierarchy', 'Derived.default'), ('hierarchy', 'Base.default')}
    default_call = next(call for call in result.find_calls(callee_name='cls.default')
                        if call.caller.qualname == 'Base.allocate')
    assert default_call.target is None
    assert any(boundary.get('call_id') == default_call.id
               and boundary['reason'] == 'dynamic_class_receiver_override_possible'
               for boundary in result.boundaries)
    assert any(not source.get('class_type')
               for source in default_call.receiver_sources)


def test_unknown_context_at_the_function_limit_keeps_a_budget_boundary():
    result = analyze('known_then_unknown', max_functions=7)
    assert len(result.functions) <= 7
    assert any(boundary['reason'] == 'budget_exceeded'
               and boundary.get('function', {}).get('qualname') == 'Base.allocate'
               for boundary in result.boundaries)


@pytest.mark.parametrize('entry', ['both', 'known_then_unknown'])
def test_multiple_receiver_contexts_obey_small_call_budgets(entry):
    result = analyze(entry, max_call_contexts=2)
    assert len(result.calls) <= 2
    assert not targets(result, 'instance.initialize')
    assert any(boundary['reason'] == 'budget_exceeded'
               for boundary in result.boundaries)
