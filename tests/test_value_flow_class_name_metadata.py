## @package tests.test_value_flow_class_name_metadata

from pathlib import Path
import runpy
import ast
from types import SimpleNamespace

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
import pcresolve.flow.analyzer as flow
import pcresolve.flow.transfer.summary_class_effects as class_effects
from pcresolve.flow.proofs import _class_name_binding
from pcresolve.flow.proofs._class_name_binding import _global_calls

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_name_metadata'


@pytest.mark.parametrize('name', ['Fresh', 'Inherited', 'Alias', 'Lookalike'])
def test_source_class_name_can_bound_a_fresh_cache_write(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    call = result.find_calls(callee_name='cls.fixed')[0]
    assert call.target.qualname == 'Base.fixed'
    assert call.class_method_bindings[0]['status'] == 'source_bound'
    effect = call.class_method_bindings[0]['lookup_preservation'][0]
    assert effect['attributes'] == ['_cache_' + name]
    metadata = effect['name_metadata']
    assert metadata['status'] == 'source_bound'
    assert metadata['value_phase'] == 'call_entry'
    assert metadata['literal'] == {'type': 'str', 'value': name}
    assert metadata['receiver_class']['qualname'] == name
    assert metadata['source_hashes'] == result.inputs['sha256']
    touch = result.find_calls(callee_name='cls.touch')[0]
    assert touch.class_metadata_bindings == [metadata]


def test_name_evidence_does_not_establish_conditional_cache_read_safety():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Conditional'))
    touch = result.find_calls(callee_name='cls.touch')[0]
    assert touch.class_metadata_bindings[0]['literal']['value'] == 'Conditional'
    assert not any(e['kind'] == 'class_attribute_write_set' for e in touch.effects)
    call = result.find_calls(callee_name='cls.fixed')[0]
    assert not any(f['status'] == 'source_bound' for f in call.class_method_bindings)


def test_exact_ordinary_helper_edges_can_use_the_same_metadata_premise():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'ordinary'))
    call = result.find_calls(callee_name='Ordinary.fixed')[0]
    assert call.target.qualname == 'Base.fixed'
    effect = call.class_method_bindings[0]['lookup_preservation'][0]
    assert effect['name_metadata']['literal']['value'] == 'Ordinary'


@pytest.mark.parametrize('name', ['DeclaredRename', 'DirectRename', 'DescriptorCreation',
                                 'GlobalEscape', 'DefaultEscape', 'MethodEscape',
                                 'DynamicWriter', 'ReflectiveWriter', 'customized',
                                 'HookChild', 'VarargAnnotation'])
def test_name_mutation_or_custom_creation_does_not_gain_a_canonical_literal(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    assert not any(f['status'] == 'source_bound' for c in result.calls
                   for f in getattr(c, 'class_metadata_bindings', []))
    assert not any(f['status'] == 'source_bound' for c in result.calls
                   if c.callee_name == 'cls.fixed' for f in c.class_method_bindings)


def test_runtime_name_subclasses_can_rebind_the_sink(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ('Fresh', 'Inherited', 'Alias', 'Lookalike'):
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    for name in ('DirectRename', 'DescriptorCreation', 'GlobalEscape',
                 'DefaultEscape', 'MethodEscape', 'Customized', 'HookChild'):
        with pytest.raises(TypeError, match='not callable'):
            values[name](old=1)
    assert values['Lookalike'].__name__ == 'Lookalike'
    with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
        values['ordinary'](old=1)


def test_metadata_budget_is_explicit_and_query_results_remain_isolated(monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    before = analyzer.analyze(FunctionRef('cases', 'Fresh'))
    snapshot = before.to_dict()
    analyzer.analyze(FunctionRef('cases', 'GlobalEscape'))
    assert analyzer.analyze(FunctionRef('cases', 'Fresh')).to_dict() == snapshot
    assert before.to_dict() == snapshot

    def exhausted(*args, **kwargs):
        raise flow._ClassEffectLimit()

    monkeypatch.setattr(class_effects, 'source_class_name_binding', exhausted)
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Fresh'))
    assert any(b['reason'] == 'class_attribute_effect_budget' for b in result.boundaries)
    assert not any(f['status'] == 'source_bound' for c in result.calls
                   if c.callee_name == 'cls.fixed' for f in c.class_method_bindings)


def test_deep_definition_expressions_hit_a_boundary_before_python_recursion():
    value = ast.Constant(value=0)
    for _ in range(100):
        value = ast.UnaryOp(op=ast.UAdd(), operand=value)
    analyzer = SimpleNamespace(module_bodies={'cases': [('cases.py', [ast.Expr(value=value)])]},
                               definitions=[(FunctionRef('cases', 'entry', 'cases.py'), None)])
    with pytest.raises(flow._ClassEffectLimit):
        _global_calls(analyzer)


@pytest.mark.parametrize('name', ['DeclaredRename', 'GlobalEscape'])
def test_rejected_metadata_does_not_spend_more_budget_on_global_activity(monkeypatch, name):
    def unexpected_scan(*args):
        raise AssertionError('An already rejected premise needs no global activity scan')

    monkeypatch.setattr(_class_name_binding, '_global_calls', unexpected_scan)
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    assert not any(f['status'] == 'source_bound' for c in result.calls
                   for f in c.class_metadata_bindings)
