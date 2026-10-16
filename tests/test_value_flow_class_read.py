## @package tests.test_value_flow_class_read

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_read'
POSITIVE = ['Fresh', 'Preloaded', 'Inherited', 'PositiveGuard', 'Alias', 'ReadOnly', 'PrivatePlain']
UNKNOWN = ['Descriptor', 'InheritedDescriptor', 'UnknownFactory', 'LaterReplace', 'DynamicSet',
           'AliasSetter', 'Written', 'ReplacedBeforeRead', 'DeletedBeforeRead', 'DirectRead',
           'ShadowedHasattr', 'Escaped', 'PrivateDescriptor', 'ReplacedMethod', 'StructuralWriter',
           'MethodEscape', 'MethodAliasEscape', 'MethodReturnEscape', 'MethodClosureEscape',
           'MethodDescriptorRead', 'NamespaceMethodReplacement', 'SiblingInvalidatesRead']


@pytest.mark.parametrize('name', POSITIVE)
def test_guarded_absent_or_plain_class_reads_preserve_downstream_lookup(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    fixed = result.find_calls(callee_name='cls.fixed')[0]
    assert fixed.target is not None and fixed.target.qualname == 'Fresh.fixed'
    assert fixed.class_method_bindings[0]['status'] == 'source_bound'
    effect = fixed.class_method_bindings[0]['lookup_preservation'][0]
    assert effect['read_basis'] == 'source_class_attribute_invariant'
    assert effect['value_completeness'] == 'unmodeled'
    premise = effect['read_premises'][0]
    assert premise['status'] == 'source_bound'
    assert premise['attribute'] == ('_PrivatePlain__cache' if name == 'PrivatePlain' else 'cache')
    assert premise['state'] == 'absent_or_builtin_literal'
    assert premise['source_hashes'] == result.inputs['sha256']
    assert premise['runtime_value_confirmed'] is False
    assert effect['read_evidence']


@pytest.mark.parametrize('name', UNKNOWN)
def test_unknown_descriptor_mutation_and_unguarded_reads_stay_unconfirmed(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    assert not any(binding['status'] == 'source_bound'
                   for call in result.find_calls(callee_name='cls.fixed')
                   for binding in call.class_method_bindings)


def test_runtime_guarded_reads_and_descriptors_have_different_targets(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    for name in POSITIVE:
        values = runpy.run_path(str(ROOT / 'cases.py'))
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    for name in ('Descriptor', 'InheritedDescriptor', 'UnknownFactory', 'Written',
                 'ReplacedBeforeRead', 'Escaped', 'PrivateDescriptor', 'MethodEscape',
                 'MethodAliasEscape', 'MethodReturnEscape', 'MethodClosureEscape'):
        values = runpy.run_path(str(ROOT / 'cases.py'))
        assert values[name](old=1) == {'old': 1}


def test_read_facts_are_query_local_and_budget_failures_stay_explicit(monkeypatch):
    from pcresolve import flow
    analyzer = FlowAnalyzer(project_root=ROOT)
    snapshot = analyzer.analyze(FunctionRef('cases', 'Fresh')).to_dict()
    analyzer.analyze(FunctionRef('cases', 'Descriptor'))
    assert analyzer.analyze(FunctionRef('cases', 'Fresh')).to_dict() == snapshot

    def exhausted(*args):
        raise flow._ClassEffectLimit()

    monkeypatch.setattr(flow, 'source_class_read_binding', exhausted)
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Fresh'))
    assert any(b['reason'] == 'class_attribute_effect_budget' for b in result.boundaries)
