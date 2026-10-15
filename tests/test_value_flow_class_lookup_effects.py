## @package tests.test_value_flow_class_lookup_effects

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef, flow

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_lookup_effects'


@pytest.mark.parametrize('name', ['CacheOnly', 'Inherited', 'SetCache', 'Conditional', 'Mangled',
                                 'Helper', 'OtherHelper', 'PosOnlyReceiver'])
def test_unrelated_class_writes_preserve_the_next_source_lookup(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=3)
    call = next(c for c in result.calls if c.callee_name in ('cls.fixed', 'receiver.fixed'))
    assert call.target.qualname == 'CacheOnly.fixed'
    fact = call.class_method_bindings[0]
    assert fact['status'] == 'source_bound'
    assert fact['lookup_preservation']
    assert any(effect['kind'] == 'class_attribute_write_set'
               for c in result.calls for effect in c.effects)


@pytest.mark.parametrize('name', ['Changed', 'ChangedHelper', 'ReturnAfterChange', 'ReboundAlias',
                                 'Private', 'ResetAfterChange', 'ArgumentChange'])
def test_rebound_method_never_regains_its_source_definition(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=3)
    calls = [c for c in result.calls if c.callee_name in (
        'cls.fixed', 'receiver.fixed', 'other.fixed', 'cls.__fixed')]
    assert calls
    assert not any(f['status'] == 'source_bound' for c in calls for f in c.class_method_bindings)


@pytest.mark.parametrize('name', ['Dynamic', 'Exposed', 'Reflected', 'WithRead', 'Aliased',
                                 'Structural', 'ShadowedSetattr', 'UncertainAlias', 'ClearsCarrier'])
def test_unsupported_class_mutation_does_not_gain_a_preservation_proof(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=3)
    calls = [c for c in result.calls if c.callee_name == 'cls.fixed']
    assert calls
    assert not any(f['status'] == 'source_bound' for c in calls for f in c.class_method_bindings)


def test_positive_and_negative_runtime_lookup_controls(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ('CacheOnly', 'Inherited', 'SetCache', 'Conditional', 'Mangled', 'Helper',
                 'OtherHelper', 'PosOnlyReceiver'):
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    for name in ('Changed', 'ChangedHelper', 'ReturnAfterChange', 'ReboundAlias', 'Private',
                 'ResetAfterChange', 'ArgumentChange'):
        assert values[name](old=1) == {'old': 1}


def test_lookup_effect_budget_is_explicit_and_cannot_prove_a_preserved_target(monkeypatch):
    def exhausted(*args, **kwargs):
        raise flow._ClassEffectLimit()

    monkeypatch.setattr(flow, 'class_attribute_writes', exhausted)
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'CacheOnly'))
    assert any(b['reason'] == 'class_attribute_effect_budget' for b in result.boundaries)
    call = result.find_calls(callee_name='cls.fixed')[0]
    assert not any(f['status'] == 'source_bound' for f in call.class_method_bindings)


def test_class_lookup_state_is_query_local():
    analyzer = FlowAnalyzer(project_root=ROOT)
    before = analyzer.analyze(FunctionRef('cases', 'CacheOnly'))
    snapshot = before.to_dict()
    analyzer.analyze(FunctionRef('cases', 'Changed'))
    analyzer.analyze(FunctionRef('cases', 'Helper'))
    assert analyzer.analyze(FunctionRef('cases', 'CacheOnly')).to_dict() == snapshot
    assert before.to_dict() == snapshot


def test_implicit_class_receiver_keyword_collision_prevents_preservation():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'ReceiverCollision'))
    call = result.find_calls(callee_name='cls.touch')[0]
    assert call.binding_status == 'invalid'
    assert any(issue['kind'] == 'duplicate_binding' and issue['parameter'] == 'cls'
               for issue in call.binding_issues)
    assert not call.effects
