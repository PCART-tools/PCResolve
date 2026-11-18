## @package tests.test_value_flow_literal_class_state

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_literal_class_state'


@pytest.mark.parametrize('name,callee', [
    ('after', 'Entry.fixed'), ('after_static', 'Static.fixed'),
    ('after_alias', 'Alias.fixed'), ('after_module', 'backend.Imported.fixed'),
    ('after_base', 'Derived.fixed'),
])
def test_literal_class_lookup_does_not_restore_a_target_after_escape(name, callee):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    call = result.find_calls(callee_name=callee)[0]
    assert call.target is None
    assert call.target_status == 'receiver_unresolved'
    assert any(value.get('value_incomplete') for value in call.receiver_sources)


@pytest.mark.parametrize('name,callee,target', [
    ('selected', 'Entry.fixed', 'Entry.fixed'),
    ('selected_static', 'Static.fixed', 'Static.fixed'),
    ('direct', 'Entry.fixed', 'Entry.fixed'),
    ('ordinary_callable', 'target', 'fixed'),
])
def test_selected_method_and_unrelated_callable_keep_their_original_target(name, callee, target):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    assert result.find_calls(callee_name=callee)[0].target.qualname == target


def test_runtime_distinguishes_lookup_before_and_after_the_argument_effect(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))

    def replacement(receiver):
        receiver.fixed = staticmethod(lambda **kwargs: kwargs)

    for name in ('after', 'after_static', 'after_alias', 'after_module', 'after_base'):
        values = runpy.run_path(str(ROOT / 'cases.py'))
        values[name].__globals__['external'] = replacement
        assert values[name](old=1) == {'old': 1}
    for name in ('selected', 'selected_static'):
        values = runpy.run_path(str(ROOT / 'cases.py'))
        values[name].__globals__['external'] = replacement
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
