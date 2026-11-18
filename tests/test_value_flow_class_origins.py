## @package tests.test_value_flow_class_origins

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_origins'


def analyze(name, analyzer=None, **limits):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module='cases', qualname=name), max_depth=4, **limits)


@pytest.mark.parametrize('entry,target', [('fixed_root', 'Fixed.generate'),
                                        ('other_root', 'Other.generate')])
def test_source_class_identity_survives_two_exact_ordinary_edges(entry, target):
    result = analyze(entry)
    call = next(c for c in result.calls if c.callee_name == 'receiver.generate')
    assert call.target.qualname == target
    assert call.class_method_bindings[0]['status'] == 'source_bound'
    origins = call.analysis_contexts[0]['parameter_facts']['receiver']
    assert origins[0]['source_class_origin']['basis'] == 'source_symbol'
    assert len(origins[0]['source_class_origin']['call_context']) == 2


@pytest.mark.parametrize('entry', ['unknown_root', 'mixed', 'escaped_root', 'patched_root',
    'deleted_root', 'hidden_escape_root', 'aliased_root', 'reassigned_root', 'global_escape_root',
    'prepared_root', 'captured_write_root', 'escaped_base_root', 'aliased_base_root'])
def test_unknown_escaped_or_modified_classes_never_become_source_bound(entry):
    result = analyze(entry)
    calls = [c for c in result.calls if c.callee_name == 'receiver.generate']
    assert calls
    assert not any(f['status'] == 'source_bound' for c in calls for f in c.class_method_bindings)
    if entry != 'mixed':
        assert all(call.target is None for call in calls)


def test_local_alias_preserves_identity_without_creating_a_new_receiver():
    call = next(c for c in analyze('local_alias_root').calls if c.callee_name == 'alias.generate')
    assert call.target.qualname == 'Fixed.generate'
    assert call.class_method_bindings[0]['status'] == 'source_bound'


def test_inherited_method_binds_the_actual_source_class():
    call = next(c for c in analyze('inherited_root').calls if c.callee_name == 'receiver.generate')
    fact = call.class_method_bindings[0]
    assert fact['status'] == 'source_bound'
    assert fact['receiver_class']['qualname'] == 'Derived'
    assert fact['definition_class']['qualname'] == 'Fixed'


def test_scan_endpoint_controls_agree_with_python_binding():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ('fixed_root', 'local_alias_root', 'inherited_root'):
        assert values[name](allowed=1) == 1
        with pytest.raises(TypeError, match='unexpected keyword argument'):
            values[name](old=1)
    assert values['other_root'](old=1) == {'old': 1}
    assert values['custom_lookup_root'](old=1) == {'old': 1}
    assert values['prepared_root'](old=1) == {'old': 1}
    assert values['escaped_base_root'](old=1) == {'old': 1}
    assert values['aliased_base_root'](old=1) == {'old': 1}


def test_source_class_identity_does_not_prove_custom_metaclass_lookup():
    result = analyze('custom_lookup_root')
    call = next(c for c in result.calls if c.callee_name == 'receiver.generate')
    assert call.class_method_bindings[0]['status'] == 'unconfirmed'
    assert any(issue['reason'] == 'class_lookup_customization'
               for issue in call.class_method_bindings[0]['issues'])
    assert call.analysis_contexts[0]['parameter_facts']['receiver'][0][
        'source_class_origin']['class']['qualname'] == 'Customized'


def test_generic_classmethod_entry_does_not_promote_its_nominal_receiver():
    result = analyze('Nominal.wrapper')
    call = next(c for c in result.calls if c.callee_name == 'cls.generate')
    assert call.class_method_bindings[0]['status'] == 'unconfirmed'
    concrete = analyze('nominal_root')
    call = next(c for c in concrete.calls if c.callee_name == 'cls.generate')
    assert call.class_method_bindings[0]['status'] == 'source_bound'


def test_parent_and_different_receiver_queries_cannot_share_source_origin_state():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyze('fixed_root', analyzer)
    snapshot = first.to_dict()
    analyze('unknown_root', analyzer)
    analyze('other_root', analyzer)
    assert analyze('fixed_root', analyzer).to_dict() == snapshot
    assert first.to_dict() == snapshot


def test_budget_retains_an_explicit_boundary_without_a_receiver_guess():
    result = analyze('fixed_root', max_functions=1, max_call_contexts=1)
    assert any('budget' in b['reason'] for b in result.boundaries)
    assert not any(c.callee_name == 'receiver.generate' and c.target for c in result.calls)
