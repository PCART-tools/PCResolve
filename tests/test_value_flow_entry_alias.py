## @package tests.test_value_flow_entry_alias

from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_entry_alias'


@pytest.mark.parametrize('name', ['public', 'Plain.first', 'Plain.second'])
def test_source_alias_keeps_the_captured_definition_after_original_name_deletion(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    assert result.entry.qualname.endswith('implementation')
    fact = result.inputs['entry_alias']
    assert fact['status'] == 'source_reference'
    assert fact['runtime_target_confirmed'] is False
    assert fact['requested']['qualname'] == name
    assert fact['source_hashes'] == result.inputs['sha256']
    assert fact['assignments']
    assert result.find_calls(callee_name='fixed')


@pytest.mark.parametrize('name', ['Rebound.alias', 'Changed.alias', 'Plain.absent', 'Absent.alias'])
def test_unknown_reassigned_or_absent_alias_is_not_selected(name):
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))


def test_alias_does_not_erase_conditional_class_activation():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Conditional.alias'))
    assert result.inputs['entry_alias']['conditions']
    assert any(item['reason'] == 'conditional_definition_unconfirmed' for item in result.boundaries)


@pytest.mark.parametrize('tail', [
    'def later(value: mutate()): pass\n',
    'result = 1 + mutate(public)\n',
    'def change():\n global public\n public = external\n',
    'public.__code__ = external\n',
    'def change(): globals()["public"] = external\n',
    'namespace = globals\ndef change(): namespace()["public"] = external\n',
])
def test_definition_effects_namespace_writes_and_function_mutation_reject_alias(tmp_path, tail):
    (tmp_path / 'cases.py').write_text('def original(**kwargs): return kwargs\n'
                                     'public = original\n' + tail)
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'public'))


def test_alias_budget_is_explicit(tmp_path):
    (tmp_path / 'cases.py').write_text('def original(**kwargs): return kwargs\n'
                                     'public = original\n' + '0\n' * 2001)
    with pytest.raises(ValueError, match='budget'):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'public'))


def test_large_module_without_requested_alias_skips_alias_audit(tmp_path, monkeypatch):
    from pcresolve import entry_alias
    (tmp_path / 'cases.py').write_text('def original(**kwargs): return kwargs\n'
                                     'public = original\n' + '0\n' * 100)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    monkeypatch.setattr(entry_alias, '_MAX_ENTRY_ALIAS_MODULE_NODES', 10)

    assert entry_alias.reference(analyzer, FunctionRef('cases', 'missing')) is None
    with pytest.raises(ValueError, match='budget'):
        entry_alias.reference(analyzer, FunctionRef('cases', 'public'))


def test_located_alias_matches_assignment_not_deleted_definition():
    path = ROOT / 'cases.py'
    line = next(index for index, text in enumerate(path.read_text().splitlines(), 1)
                if 'first = second' in text)
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Plain.first', str(path), line))
    assert result.inputs['entry_alias']['assignments'][-1]['evidence']['lineno'] == line
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'Plain.first', str(path), line + 1))


@pytest.mark.parametrize('tail', [
    'Plain.alias.__code__ = external\n',
    'def change(): Plain.alias.__code__ = external\n',
    'setattr(Plain, "alias", external)\n',
    'def change():\n global Plain\n Plain = external\n',
])
def test_class_alias_rejects_visible_namespace_or_function_changes(tmp_path, tail):
    (tmp_path / 'cases.py').write_text('class Plain:\n'
                                     ' def implementation(self, **kwargs): return kwargs\n'
                                     ' alias = implementation\n del implementation\n' + tail)
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'Plain.alias'))


def test_isolated_child_does_not_inherit_the_parent_alias_selector():
    analyzer = FlowAnalyzer(project_root=ROOT)
    result = analyzer.analyze(FunctionRef('cases', 'public'))
    before = result.to_dict()
    child = analyzer.expand(result, result.find_calls(callee_name='fixed')[0].id, isolate=True)
    assert child.entry.qualname == 'fixed'
    assert 'entry_alias' not in child.inputs
    assert result.to_dict() == before
