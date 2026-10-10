## @package tests.test_value_flow_index_reuse
#  Reused source facts never reuse mutable query state or stale file versions.

import ast
import os

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
import pcresolve.flow as flow_module


ENTRY = FunctionRef(module='main', qualname='entry')
SOURCE = ('def helper(value): return value\n'
          'def entry(value): return helper(value)\n')


def test_repeated_flow_queries_build_definition_index_once(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text(SOURCE, encoding='utf-8')
    original = flow_module.DefinitionIndex
    indexed = []

    def build(records):
        indexed.append(len(records))
        return original(records)

    monkeypatch.setattr(flow_module, 'DefinitionIndex', build)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    before = analyzer.analyze(ENTRY, max_depth=2)
    tree = ast.dump(analyzer._source_snapshot.documents[str(tmp_path / 'main.py')].tree,
                    include_attributes=True)
    after = analyzer.analyze(ENTRY, max_depth=2)
    assert before.to_dict() == after.to_dict()
    assert ast.dump(analyzer._source_snapshot.documents[str(tmp_path / 'main.py')].tree,
                    include_attributes=True) == tree
    assert len(indexed) == 1


def test_reuse_refreshes_same_size_same_mtime_sources(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    before = analyzer.analyze(ENTRY, max_depth=2)
    stat = path.stat()
    path.write_text(SOURCE.replace('return value', 'return False'), encoding='utf-8')
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert path.stat().st_size == stat.st_size
    after = analyzer.analyze(ENTRY, max_depth=2)
    assert after.inputs['sha256'] != before.inputs['sha256']
    assert before.trace_parameter('value')['status'] == 'flow_found'
    assert after.trace_parameter('value')['status'] == 'unknown'


@pytest.mark.parametrize('change', ['add', 'remove', 'delete', 'syntax', 'roots'])
def test_source_set_errors_and_import_roots_invalidate_index(tmp_path, change):
    path = tmp_path / 'main.py'
    path.write_text(SOURCE, encoding='utf-8')
    extra = tmp_path / 'extra.py'
    extra.write_text('def other(value): return value\n', encoding='utf-8')
    analyzer = FlowAnalyzer(source_files=[path, extra], import_roots=[tmp_path])
    old = analyzer.analyze(ENTRY, max_depth=2).to_dict()
    entry = ENTRY
    if change == 'add':
        added = tmp_path / 'added.pyi'
        added.write_text('def declared(value): ...\n', encoding='utf-8')
        analyzer.add_files([added])
    elif change == 'remove':
        analyzer.files.remove(str(extra))
    elif change == 'delete':
        extra.unlink()
    elif change == 'syntax':
        extra.write_text('def broken(:\n', encoding='utf-8')
    else:
        analyzer.roots = [str(tmp_path.parent)]
        entry = FunctionRef(module=tmp_path.name + '.main', qualname='entry')
    current = analyzer.analyze(entry, max_depth=2)
    fresh = FlowAnalyzer(source_files=analyzer.files, import_roots=analyzer.roots)
    assert current.to_dict() == fresh.analyze(entry, max_depth=2).to_dict()
    assert current.to_dict() != old
    if change in ('delete', 'syntax'):
        extra.write_text('def other(value): return value\n', encoding='utf-8')
        assert analyzer.analyze(ENTRY, max_depth=2).to_dict() == old


def test_reuse_resets_budgets_contracts_and_result_objects(tmp_path):
    (tmp_path / 'main.py').write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    before = analyzer.analyze(ENTRY, max_depth=2)
    saved = before.to_dict()
    limited = analyzer.analyze(ENTRY, max_depth=2, max_functions=1, max_call_contexts=1)
    fresh = FlowAnalyzer(project_root=tmp_path)
    assert limited.to_dict() == fresh.analyze(
        ENTRY, max_depth=2, max_functions=1, max_call_contexts=1).to_dict()
    analyzer.parameter_shapes = {'main.entry': {
        'parameters': {'value': 'list'}, 'provenance': 'test contract'}}
    fresh.parameter_shapes = analyzer.parameter_shapes
    analyzer.return_summaries = {'external.identity': {
        'parameters': ['value'], 'returns': [], 'provenance': 'test contract'}}
    fresh.return_summaries = analyzer.return_summaries
    assert analyzer.analyze(ENTRY, max_depth=3).to_dict() == fresh.analyze(
        ENTRY, max_depth=3).to_dict()
    assert before.to_dict() == saved
    before.calls[0].argument_sources.clear()
    assert analyzer.analyze(ENTRY, max_depth=3).to_dict() == fresh.analyze(
        ENTRY, max_depth=3).to_dict()
