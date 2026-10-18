## @package tests.test_value_flow_class_finite_iteration

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_finite_iteration'


def lookup(name, analyzer=None):
    result = (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef('cases', name), max_depth=3)
    return result, result.find_calls(callee_name='cls.fixed')[0]


@pytest.mark.parametrize('name', ['Aliases', 'Empty'])
def test_finite_unrelated_writes_preserve_the_following_class_lookup(name):
    _, call = lookup(name)
    assert call.target.qualname == 'Base.fixed'
    binding = call.class_method_bindings[0]
    assert binding['status'] == 'source_bound'
    effects = binding['lookup_preservation']
    assert any(effect['attributes'] == (['get_lw', 'get_ec', 'set_lw', 'set_ec']
                                      if name == 'Aliases' else ['cache']) for effect in effects)


@pytest.mark.parametrize('name', ['Changed', 'Unknown', 'Escaped', 'BranchChanged'])
def test_changed_or_unbounded_loop_cannot_preserve_a_method(name):
    _, call = lookup(name)
    assert not any(fact['status'] == 'source_bound' for fact in call.class_method_bindings)


def test_runtime_controls_distinguish_unrelated_writes_from_method_replacement():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ['Aliases', 'Empty']:
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    for name in ['Changed', 'BranchChanged']:
        assert values[name](old=1) == {'old': 1}


def test_loop_effects_remain_query_local():
    analyzer = FlowAnalyzer(project_root=ROOT)
    before, _ = lookup('Aliases', analyzer)
    snapshot = before.to_dict()
    lookup('Changed', analyzer)
    lookup('Unknown', analyzer)
    after, _ = lookup('Aliases', analyzer)
    assert before.to_dict() == after.to_dict() == snapshot
