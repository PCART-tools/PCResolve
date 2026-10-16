## @package tests.test_value_flow_class_escape_aliases

from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef, flow

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_escape_aliases'
ESCAPED = ['ListEscape', 'DictEscape', 'TupleAliasEscape', 'BranchContainerEscape',
           'LambdaEscape', 'ReturnEscape', 'StoredEscape', 'ProjectedWrite',
           'DestructuredEscape', 'InvokedCapture', 'DefaultCapture', 'ExtendedContainer']
PRESERVED = ['DormantContainer', 'ShadowedContainer', 'UnrelatedContainer', 'ShadowedLambda']


@pytest.mark.parametrize('name', ESCAPED)
def test_contained_and_deferred_class_escape_invalidates_metadata(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    metadata = result.find_calls(callee_name='cls.touch')[0].class_metadata_bindings[0]
    assert metadata['status'] == 'unconfirmed'
    assert 'literal' not in metadata
    assert any(issue['reason'] == 'class_name_source_escape'
               and issue['evidence']['file_path'] == str(ROOT.resolve() / 'cases.py')
               for issue in metadata['issues'])
    assert not any(binding['status'] == 'source_bound'
                   for call in result.find_calls(callee_name='cls.fixed')
                   for binding in call.class_method_bindings)


@pytest.mark.parametrize('name', PRESERVED)
def test_unescaped_containers_and_lexical_shadowing_preserve_metadata(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    metadata = result.find_calls(callee_name='cls.touch')[0].class_metadata_bindings[0]
    assert metadata['status'] == 'source_bound'
    assert metadata['literal']['value'] == name


def test_custom_constructor_result_is_not_assumed_to_be_an_instance():
    analyzer = FlowAnalyzer(project_root=ROOT)
    analyzer.analyze(FunctionRef('cases', 'DormantContainer'))
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    assert any(ref.qualname == 'ConstructorEscape' and reason == 'visible_class_escape'
               for ref, _, reason, _, _ in writes)


def test_runtime_container_and_callback_mutation_replaces_the_sink(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    values = runpy.run_path(str(ROOT / 'cases.py'))
    for name in ESCAPED:
        with pytest.raises(TypeError, match='not callable'):
            values[name](old=1)
    for name in PRESERVED:
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    assert type(values['ConstructorEscape'].__name__) is not str
    assert values['ConstructorEscape'].__name__ == 'renamed'


def test_escape_index_budget_and_query_order_remain_conservative(monkeypatch):
    analyzer = FlowAnalyzer(project_root=ROOT)
    before = analyzer.analyze(FunctionRef('cases', 'DormantContainer')).to_dict()
    for name in reversed(ESCAPED):
        analyzer.analyze(FunctionRef('cases', name))
    assert analyzer.analyze(FunctionRef('cases', 'DormantContainer')).to_dict() == before
    monkeypatch.setattr(flow, '_CLASS_BINDING_NODE_LIMIT', 10)
    bounded = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'DormantContainer'))
    assert not any(binding['status'] == 'source_bound' for call in bounded.calls
                   for binding in call.class_metadata_bindings)
    assert bounded.boundaries
