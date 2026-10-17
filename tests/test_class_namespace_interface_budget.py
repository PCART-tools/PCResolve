## @package tests.test_class_namespace_interface_budget

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve._constructor_entry import _definition_issues
from pcresolve.class_attribute_effects import _ClassEffectLimit


def source(tmp_path, signature='', decorator='', tail=''):
    path = tmp_path / 'sample.py'
    path.write_text('''class Entry:
    def __init__(self, **kwargs):
        pass
''' + decorator + '    def unrelated(self' + signature + '):\n'
        + '        0\n' * 3000 + tail, encoding='utf-8')
    return path


def test_deferred_method_body_does_not_exhaust_namespace_formation_budget(tmp_path):
    source(tmp_path)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'Entry'))
    assert result.inputs['entry_binding']['status'] == 'source_bound'


@pytest.mark.parametrize('signature,decorator', [
    (', value=effect()', ''),
    (', value: effect() = None', ''),
    ('', '    @effect\n'),
])
def test_definition_expressions_are_still_checked(tmp_path, signature, decorator):
    source(tmp_path, signature, decorator)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    hierarchy = analyzer._class_mro('sample', 'Entry')
    assert _definition_issues(analyzer, hierarchy)


def test_large_evaluated_default_still_exhausts_namespace_budget(tmp_path):
    source(tmp_path, ', value=(' + '0,' * 3000 + ')')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    with pytest.raises(_ClassEffectLimit):
        _definition_issues(analyzer, analyzer._class_mro('sample', 'Entry'))


def test_deferred_body_does_not_hide_visible_constructor_replacement(tmp_path):
    source(tmp_path, tail='        Entry.__new__ = replacement\n')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    try:
        result = analyzer.analyze(FunctionRef('sample', 'Entry'))
    except ValueError:
        return
    assert result.inputs['entry_binding']['status'] != 'source_bound'
