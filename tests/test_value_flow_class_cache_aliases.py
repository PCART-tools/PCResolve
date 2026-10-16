## @package tests.test_value_flow_class_cache_aliases

from pathlib import Path
import runpy
import ast

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_cache_aliases'
PRESERVED = ['Local', 'Alias', 'Annotated', 'Branches', 'ReboundOriginal',
             'ReboundAfterWrite', 'Primitive', 'Metadata', 'ConditionalRead', 'AnnotationOnly', 'Chained']
UNKNOWN = ['Rebound', 'ReboundAlias', 'UnknownBranch', 'MissingBranch', 'ReplacedAttribute',
           'ConditionalExisting', 'ParameterValue', 'UnknownFactory', 'ProtectedAlias',
           'DeletedCache', 'BranchRebind']


@pytest.mark.parametrize('name', PRESERVED)
def test_local_builtin_payload_aliases_preserve_unaffected_class_lookup(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    touch = result.find_calls(callee_name='cls.touch')[0]
    effects = [effect for effect in touch.effects if effect['kind'] == 'class_attribute_write_set']
    assert len(effects) == 1
    effect = effects[0]
    assert effect['value_completeness'] == 'unmodeled'
    assert effect['attributes'] == ['_cache_Metadata' if name == 'Metadata' else 'cache']
    assert len(effect['evidence']) >= 3
    fixed = result.find_calls(callee_name='cls.fixed')[0]
    assert fixed.class_method_bindings[0]['status'] == 'source_bound'
    assert fixed.target.qualname == 'Base.fixed'


@pytest.mark.parametrize('name', UNKNOWN)
def test_unknown_reassigned_or_preexisting_values_do_not_prove_read_safety(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    touch = result.find_calls(callee_name='cls.touch')[0]
    assert not any(effect['kind'] == 'class_attribute_write_set' for effect in touch.effects)
    assert not any(binding['status'] == 'source_bound'
                   for call in result.find_calls(callee_name='cls.fixed')
                   for binding in call.class_method_bindings)


def test_runtime_local_values_and_descriptor_replacements(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in PRESERVED:
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    for name in ('Rebound', 'ReboundAlias', 'UnknownBranch', 'ReplacedAttribute', 'UnknownFactory',
                 'BranchRebind'):
        assert values[name](old=1) == {'old': 1}
    with pytest.raises(UnboundLocalError):
        values['MissingBranch'](old=1)
    with pytest.raises(AttributeError):
        values['DeletedCache'](old=1)
    values['ConditionalExisting'].cache = values['Trap']()
    assert values['ConditionalExisting'](old=1) == {'old': 1}


def test_alias_proofs_are_isolated_from_prior_unknown_queries():
    analyzer = FlowAnalyzer(project_root=ROOT)
    before = analyzer.analyze(FunctionRef('cases', 'Branches')).to_dict()
    for name in UNKNOWN:
        analyzer.analyze(FunctionRef('cases', name))
    assert analyzer.analyze(FunctionRef('cases', 'Branches')).to_dict() == before


@pytest.mark.parametrize('name', ['Alias', 'Branches', 'Annotated'])
def test_literal_alias_and_branch_origins_remain_in_the_effect_evidence(name):
    tree = ast.parse((ROOT / 'cases.py').read_text(encoding='utf-8'))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
    assignments = {node.lineno for node in ast.walk(owner)
                   if isinstance(node, (ast.Assign, ast.AnnAssign))}
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    call = result.find_calls(callee_name='cls.touch')[0]
    effect = next(value for value in call.effects if value['kind'] == 'class_attribute_write_set')
    assert assignments <= {source['lineno'] for source in effect['evidence']}
