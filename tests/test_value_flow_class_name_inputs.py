## @package tests.test_value_flow_class_name_inputs

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_name_inputs'


@pytest.mark.parametrize('name', ['Positional', 'Keyword', 'KeywordOnly', 'Helper', 'clean'])
def test_exact_literal_name_arguments_bound_the_written_attributes(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=3)
    call = next(c for c in result.calls if c.callee_name.endswith('.fixed'))
    assert call.target.qualname == 'Base.fixed'
    fact = call.class_method_bindings[0]
    assert fact['status'] == 'source_bound'
    effect = fact['lookup_preservation'][0]
    assert effect['attributes'] == ['cache' if name in ('Helper', 'KeywordOnly', 'clean')
                                    else 'cache_value']
    assert effect['name_bindings'][0]['parameter'] == 'name'
    assert effect['name_bindings'][0]['literal'] == {'type': 'str', 'value': 'cache'}


@pytest.mark.parametrize('name', ['Changed', 'Uncertain', 'Divergent', 'Default', 'Metadata',
                                 'Local', 'ReboundInput', 'DuplicateInput', 'changed'])
def test_changed_or_unproven_names_do_not_preserve_the_next_lookup(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name), max_depth=3)
    calls = [c for c in result.calls if c.callee_name.endswith('.fixed')]
    if name == 'Metadata':
        assert result.inputs['entry_binding']['status'] == 'unconfirmed'
    else:
        assert calls
    assert not any(f['status'] == 'source_bound' for call in calls for f in call.class_method_bindings)


def test_source_name_inputs_have_independent_runtime_controls():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ('Positional', 'Keyword', 'KeywordOnly', 'Local', 'Helper', 'Default', 'clean'):
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    for name in ('Changed', 'Divergent', 'Metadata', 'ReboundInput', 'changed'):
        assert values[name](old=1) == {'old': 1}
    assert values['Uncertain'](name='fixed', old=1) == {'old': 1}
    assert type(values['Metadata'].__name__) is values['Name']
    with pytest.raises(TypeError, match='multiple values'):
        values['DuplicateInput'](old=1)


def test_each_incoming_name_keeps_its_own_class_state():
    analyzer = FlowAnalyzer(project_root=ROOT)
    first = analyzer.analyze(FunctionRef('cases', 'Helper'))
    snapshot = first.to_dict()
    analyzer.analyze(FunctionRef('cases', 'Changed'))
    analyzer.analyze(FunctionRef('cases', 'Metadata'))
    analyzer.analyze(FunctionRef('cases', 'changed'))
    assert analyzer.analyze(FunctionRef('cases', 'Helper')).to_dict() == snapshot
    assert first.to_dict() == snapshot
