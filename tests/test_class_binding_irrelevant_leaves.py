## @package tests.test_class_binding_irrelevant_leaves

import pytest

from pcresolve import FlowAnalyzer, FunctionRef, flow


def project(tmp_path, tail=''):
    (tmp_path / 'a_data.py').write_text('DATA = (' + '0,' * 2000 + ')\n', encoding='utf-8')
    (tmp_path / 'entry.py').write_text('''class Entry:
    def __init__(self, **kwargs):
        self.value = kwargs.pop('legacy', 0)
''' + tail, encoding='utf-8')


def test_literal_leaves_do_not_exhaust_class_binding_proof_work(tmp_path, monkeypatch):
    project(tmp_path)
    monkeypatch.setattr(flow, '_CLASS_BINDING_NODE_LIMIT', 80)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    result = analyzer.analyze(FunctionRef('entry', 'Entry'))
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    assert result.inputs['entry_binding']['retained_instance_attribute_stores']
    assert not analyzer._class_binding_writes(include_escapes=True)[1]


@pytest.mark.parametrize('tail,reason', [
    ('Entry.__setattr__ = replacement\n', 'visible_method_write'),
    ("setattr(Entry, '__setattr__', replacement)\n", 'visible_dynamic_attribute_write'),
    ('external([Entry])\n', 'visible_class_escape'),
    ("external({'selected': Entry})\n", 'visible_class_escape'),
    ('callback = lambda: Entry\nexternal(callback)\n', 'visible_class_escape'),
])
def test_late_writes_and_escapes_survive_large_literal_data(tmp_path, monkeypatch, tail, reason):
    project(tmp_path, tail)
    monkeypatch.setattr(flow, '_CLASS_BINDING_NODE_LIMIT', 120)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    result = analyzer.analyze(FunctionRef('entry', 'Entry'))
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    assert any(ref.qualname == 'Entry' and kind == reason for ref, _, kind, _, _ in writes)
    assert not result.inputs['entry_binding']['retained_instance_attribute_stores']


def test_relevant_work_still_exhausts_the_explicit_budget(tmp_path, monkeypatch):
    project(tmp_path, 'external([Entry])\n' * 100)
    monkeypatch.setattr(flow, '_CLASS_BINDING_NODE_LIMIT', 80)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    assert analyzer._class_binding_writes(include_escapes=True)[1]
