## @package tests.test_value_flow_class_helper_defaults

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_helper_defaults'


@pytest.mark.parametrize('name', ['direct', 'aliased', 'keyword', 'local'])
def test_mutated_ordinary_defaults_cannot_preserve_class_lookups(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    calls = [c for c in result.calls if c.callee_name.endswith('.fixed')]
    assert calls
    assert not any(f['status'] == 'source_bound' for c in calls for f in c.class_method_bindings)
    assert not any(e['kind'] == 'class_attribute_write_set' for c in result.calls for e in c.effects)


def test_explicit_none_is_a_supplied_literal_not_an_assumed_default():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'explicit'))
    call = result.find_calls(callee_name='Explicit.fixed')[0]
    assert call.target.qualname == 'Base.fixed'
    assert call.class_method_bindings[0]['status'] == 'source_bound'


def test_runtime_default_aliases_rebind_the_sink_and_explicit_none_does_not():
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ('direct', 'aliased', 'keyword', 'local'):
        assert values[name](old=1) == {'old': 1}
    for name in ('explicit', 'unused'):
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)


def test_default_mutation_queries_do_not_invalidate_an_independent_explicit_call():
    analyzer = FlowAnalyzer(project_root=ROOT)
    before = analyzer.analyze(FunctionRef('cases', 'explicit'))
    snapshot = before.to_dict()
    for name in ('direct', 'aliased', 'local', 'keyword'):
        analyzer.analyze(FunctionRef('cases', name))
    assert analyzer.analyze(FunctionRef('cases', 'explicit')).to_dict() == snapshot
    assert before.to_dict() == snapshot
