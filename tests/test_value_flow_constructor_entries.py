## @package tests.test_value_flow_constructor_entries

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from tests.flow_test_support import set_class_binding_limit
import pcresolve.flow.analyzer as flow
import pcresolve.flow.index.definitions as flow_definitions

ROOT = Path(__file__).parent / 'fixtures/value_flow_constructor_bindings'


@pytest.mark.parametrize('name,target', [
    ('FixedNew', 'FixedNew.__new__'), ('DerivedNew', 'FixedNew.__new__'),
    ('Allocates', 'FixedNew.__new__'), ('SkipsInit', 'SkipsInit.__new__'),
    ('OrdinaryInit', 'OrdinaryInit.__init__'),
    ('InheritedInit', 'OrdinaryInit.__init__'),
    ('OpenDerived', 'FixedNew.__new__'),
])
def test_class_entry_selects_a_phase_and_retains_the_actual_class(name, target):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=3)
    assert result.entry.qualname == target
    fact = result.inputs['entry_binding']
    assert fact['status'] == 'source_bound'
    assert fact['query_kind'] == 'source_class_call'
    assert fact['receiver_class']['qualname'] == name
    assert fact['target']['qualname'] == target
    assert fact['runtime_target_confirmed'] is False
    assert fact['source_hashes']
    if target.endswith('__new__'):
        assert fact['execution_scope'] == 'new_invocation_only'
        assert any(b['reason'] == 'constructor_initialization_unmodeled'
                   for b in result.boundaries)
    if name in ('FixedNew', 'DerivedNew', 'Allocates'):
        call = next(c for c in result.calls if c.callee_name == 'cls.fixed')
        assert call.class_method_bindings[0]['status'] == 'source_bound'
        assert call.class_method_bindings[0]['receiver_class']['qualname'] == name


@pytest.mark.parametrize('name', ['CustomizedInit', 'AssignedNew', 'InheritedRebound',
                                 'HookedInit', 'CustomDescriptorNew', 'DeferredNew'])
def test_unproven_class_entry_does_not_supply_body_calls(name):
    analyzer = FlowAnalyzer(project_root=ROOT)
    try:
        result = analyzer.analyze(FunctionRef('cases', name), max_depth=3)
    except ValueError:
        return
    assert result.inputs['entry_binding']['status'] == 'unconfirmed'
    assert not result.calls
    assert any(b['reason'] == 'constructor_entry_unconfirmed' for b in result.boundaries)


def test_class_entry_and_generic_method_queries_keep_separate_contexts():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyzer.analyze(FunctionRef('cases', 'DerivedNew'))
    before = first.to_dict()
    generic = analyzer.analyze(FunctionRef('cases', 'FixedNew.__new__'))
    call = next(c for c in generic.calls if c.callee_name == 'cls.fixed')
    assert call.class_method_bindings[0]['status'] == 'unconfirmed'
    analyzer.analyze(FunctionRef('cases', 'Allocates'))
    assert analyzer.analyze(FunctionRef('cases', 'DerivedNew')).to_dict() == before
    assert first.to_dict() == before


def test_class_entry_binding_budget_is_explicit(monkeypatch):
    set_class_binding_limit(monkeypatch, 1)
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'FixedNew'))
    assert result.inputs['entry_binding']['status'] == 'unconfirmed'
    assert any(issue['reason'] == 'constructor_binding_budget'
               for issue in result.inputs['entry_binding']['issues'])


def test_inherited_allocator_uses_the_query_class_override():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'OpenDerived'))
    call = next(c for c in result.calls if c.callee_name == 'cls.fixed')
    assert call.target.qualname == 'OpenDerived.fixed'
    assert call.class_method_bindings[0]['status'] == 'source_bound'
    values = runpy.run_path(str(ROOT / 'cases.py'))
    assert values['OpenDerived'](old=1) == {'old': 1}


def test_class_entry_expansion_and_function_budget_preserve_the_parent():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyzer.analyze(FunctionRef('cases', 'DerivedNew'))
    before = first.to_dict()
    expanded = analyzer.expand(first, next(c.id for c in first.calls if c.callee_name == 'cls.fixed'))
    assert any(f['function']['qualname'] == 'FixedNew.fixed' for f in expanded.functions)
    assert first.to_dict() == before
    limited = analyzer.analyze(FunctionRef('cases', 'DerivedNew'), max_depth=3, max_functions=1)
    assert any(b['reason'] == 'budget_exceeded' for b in limited.boundaries)


@pytest.mark.parametrize('name,phase', [('OverloadedInit', '__init__'),
                                      ('OverloadedNew', '__new__')])
def test_import_backed_overload_declarations_select_one_final_implementation(name, phase):
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef('overloaded', name))
    assert result.entry.qualname == name + '.' + phase
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    assert result.find_calls(callee_name='fixed')
    if phase == '__new__':
        call = analyzer.analyze(FunctionRef('overloaded', 'call_new')).find_calls(
            callee_name='OverloadedNew')[0]
        assert call.constructor_bindings[0]['status'] == 'source_bound'


def test_effectful_overload_defaults_do_not_establish_entry_binding():
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('overloaded', 'EffectfulStub'))


@pytest.mark.parametrize('prefix,body', [
    ('overload = lambda function: function\n', '''class Entry:
    @overload
    def __init__(self, allowed: int): ...
    def __init__(self, **kwargs): pass
'''),
    ('', '''class Entry:
    overload = lambda function: function
    @overload
    def __init__(self, allowed: int): ...
    def __init__(self, **kwargs): pass
'''),
    ('', '''class Entry:
    def __init__(self, **kwargs): pass
    @overload
    def __init__(self, allowed: int): ...
'''),
])
def test_shadowed_or_last_overload_declarations_do_not_select_an_implementation(
        tmp_path, prefix, body):
    (tmp_path / 'sample.py').write_text('from typing import overload\n' + prefix + body,
                                      encoding='utf-8')
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'Entry'))
