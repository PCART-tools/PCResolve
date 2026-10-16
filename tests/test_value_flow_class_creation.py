## @package tests.test_value_flow_class_creation

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve import _class_definition

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_creation'
REPLACED = [('Hidden', 'hidden'), ('DescriptorEntry', 'descriptor'),
            ('AnnotationEntry', 'annotation'), ('FactoryEntry', 'factory'),
            ('WrittenDescriptor', 'written'), ('ShadowedFactory', 'shadowed')]


@pytest.mark.parametrize('name,wrapper', REPLACED)
def test_class_definition_execution_cannot_bind_the_old_constructor(name, wrapper):
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef('cases', name), max_depth=3)
    assert result.inputs['entry_binding']['status'] == 'unconfirmed'
    assert any(issue.get('evidence', {}).get('file_path') == str(ROOT.resolve() / 'cases.py')
               for issue in result.inputs['entry_binding']['issues'])
    assert not result.calls
    assert any(b['reason'] == 'constructor_entry_unconfirmed' for b in result.boundaries)

    nested = analyzer.analyze(FunctionRef('cases', wrapper), max_depth=3)
    call = nested.find_calls(callee_name=name)[0]
    assert call.constructor_bindings[0]['status'] == 'unconfirmed'
    assert call.constructor_bindings[0]['issues']


@pytest.mark.parametrize('name', ['Base', 'Literal', 'Derived', 'DescriptorSafe'])
def test_literal_namespaces_and_builtin_method_descriptors_keep_the_source_phase(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    assert result.entry.qualname == 'Base.__new__'
    assert result.find_calls(callee_name='fixed')


def test_runtime_creation_hooks_replace_the_allocator(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name, wrapper in REPLACED:
        assert values[name](old=1) == {'old': 1}
        assert values[wrapper](old=1) == {'old': 1}
    for name in ('Base', 'Literal', 'Derived', 'DescriptorSafe'):
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)


def test_plain_source_instance_premises_retain_their_source_dependencies():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef('cases', 'DescriptorSafe'))
    assert str(ROOT.resolve() / 'creation_support.py') in result.inputs['entry_binding']['source_hashes']
    result = analyzer.analyze(FunctionRef('cases', 'descriptor_safe'))
    fact = result.find_calls(callee_name='DescriptorSafe')[0].constructor_bindings[0]
    assert fact['status'] == 'source_bound'
    assert str(ROOT.resolve() / 'creation_support.py') in fact['source_hashes']


def test_class_creation_rejection_does_not_contaminate_other_queries():
    analyzer = FlowAnalyzer(project_root=ROOT)
    before = analyzer.analyze(FunctionRef('cases', 'Literal'))
    snapshot = before.to_dict()
    for name, wrapper in REPLACED:
        analyzer.analyze(FunctionRef('cases', wrapper))
        analyzer.analyze(FunctionRef('cases', name))
    assert analyzer.analyze(FunctionRef('cases', 'Literal')).to_dict() == snapshot
    assert before.to_dict() == snapshot


def test_definition_budget_blocks_both_root_and_explicit_constructor_proofs(monkeypatch):
    monkeypatch.setattr(_class_definition, '_CLASS_DEFINITION_NODE_LIMIT', 1)
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef('cases', 'Base'))
    fact = result.inputs['entry_binding']
    assert fact['status'] == 'unconfirmed'
    assert {'reason': 'constructor_class_definition_budget'} in fact['issues']
    result = analyzer.analyze(FunctionRef('cases', 'hidden'))
    fact = result.find_calls(callee_name='Hidden')[0].constructor_bindings[0]
    assert fact['status'] == 'unconfirmed'
    assert {'reason': 'constructor_class_definition_budget'} in fact['issues']
