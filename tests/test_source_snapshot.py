## @package tests.test_source_snapshot
#  Source snapshots refresh content and keep consumer compatibility policies explicit.

import ast
import hashlib
import os
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.ownership.analyzer import ProjectAnalyzer
from pcresolve.frontend.module_mapper import ModuleMapper
from pcresolve.frontend.source_snapshot import (SourceStore, ModuleIndex, module_name_for_path,
                                      OWNERSHIP_SOURCE, FLOW_SOURCE,
                                      OWNERSHIP_MODULES, FLOW_MODULES)


def test_incremental_documents_share_parse_with_flow_without_skipping_refresh(tmp_path, monkeypatch):
    from pcresolve.frontend.source_snapshot import SourceReadPolicy
    import pcresolve.frontend.source_snapshot as sources
    path = tmp_path / 'module.py'
    path.write_text('def entry(x): return x\n', encoding='utf-8')
    store = SourceStore()
    parser = sources.ast.parse
    calls = []
    def counted(text, *args, **kwargs):
        calls.append(text)
        return parser(text, *args, **kwargs)
    monkeypatch.setattr(sources.ast, 'parse', counted)
    first = store.read_document(str(path), SourceReadPolicy('tokenize', True))
    analyzer = FlowAnalyzer(source_files=[path], import_roots=[tmp_path], source_store=store)
    result = analyzer.analyze(FunctionRef('module', 'entry'))
    assert result.inputs['sha256'][str(path)] == first.sha256
    assert len(calls) == 1
    path.write_text('def entry(x): return 0\n', encoding='utf-8')
    changed = analyzer.analyze(FunctionRef('module', 'entry'))
    assert changed.inputs['sha256'][str(path)] != first.sha256
    assert len(calls) == 2


def test_declared_encoding_does_not_make_flow_accept_non_utf8(tmp_path):
    from pcresolve.frontend.source_snapshot import SourceReadPolicy
    path = str(tmp_path / 'latin.py')
    Path(path).write_bytes(b'# coding: latin-1\nvalue = "\xe9"\n')
    store = SourceStore()
    document = store.read_document(path, SourceReadPolicy('tokenize', True))
    assert document.error is None
    assert store.snapshot([path], FLOW_SOURCE).documents[path].error_stage == 'read'


def test_shared_reader_does_not_widen_analyzer_source_scope(tmp_path):
    paths = [tmp_path / name for name in ('selected.py', 'outside.py')]
    for path in paths:
        path.write_text('def entry(): return 0\n', encoding='utf-8')
    store = SourceStore()
    for path in paths:
        store.read_document(str(path), FLOW_SOURCE)
    result = FlowAnalyzer(source_files=paths[:1], import_roots=[tmp_path], source_store=store).analyze(
        FunctionRef('selected', 'entry'))
    assert result.inputs['source_files'] == [str(paths[0])]


def test_shared_reader_preserves_analysis_limits(tmp_path):
    from pcresolve import AnalysisLimits, AnalysisLimitExceeded
    path = tmp_path / 'module.py'
    path.write_text('def entry(x):\n    return x + 1\n', encoding='utf-8')
    store = SourceStore()
    store.read_document(str(path), FLOW_SOURCE)
    analyzer = FlowAnalyzer(source_files=[path], import_roots=[tmp_path], source_store=store,
                            analysis_limits=AnalysisLimits(max_work=1))
    with pytest.raises(AnalysisLimitExceeded):
        analyzer.analyze(FunctionRef('module', 'entry'))


def test_strict_syntax_query_does_not_evict_compatible_historical_ast(tmp_path):
    from pcresolve.frontend.source_snapshot import SourceReadPolicy
    path = str(tmp_path / 'legacy.py')
    Path(path).write_text('x.async()\n', encoding='utf-8')
    store = SourceStore()
    historical = store.read_document(path, FLOW_SOURCE)
    assert historical.error is None
    strict = store.read_document(path, SourceReadPolicy('tokenize'))
    assert isinstance(strict.error, SyntaxError)
    assert store.read_document(path, FLOW_SOURCE) is historical


ROOT = Path(__file__).parent / 'fixtures' / 'source_snapshot'


def test_snapshot_reads_text_hash_and_source_positions_from_one_version(tmp_path):
    path = tmp_path / 'main.py'
    path.write_bytes(b'def entry(value):\r\n    return value\r\n')
    snapshot = SourceStore().snapshot([str(path)], FLOW_SOURCE)
    document = snapshot.documents[str(path)]
    assert document.text == 'def entry(value):\n    return value\n'
    assert document.sha256 == hashlib.sha256(document.text.encode('utf-8')).hexdigest()
    assert document.tree.body[0].lineno == 1
    assert document.tree.body[0].body[0].end_lineno == 2
    assert document.error is None
    with pytest.raises(TypeError):
        snapshot.documents[str(path)] = document


def test_unchanged_decoded_sources_share_ast_across_read_policies():
    path = str(ROOT / 'pkg/helpers.py')
    store = SourceStore()
    owner = store.snapshot([path], OWNERSHIP_SOURCE).documents[path]
    flow = store.snapshot([path], FLOW_SOURCE).documents[path]
    assert owner.tree is flow.tree


def test_changed_content_is_detected_even_with_unchanged_size_and_mtime(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('value = first\n', encoding='utf-8')
    store = SourceStore()
    before = store.snapshot([str(path)], FLOW_SOURCE).documents[str(path)]
    stat = path.stat()
    path.write_text('value = other\n', encoding='utf-8')
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    after = store.snapshot([str(path)], FLOW_SOURCE).documents[str(path)]
    assert path.stat().st_size == stat.st_size
    assert after.sha256 != before.sha256 and after.tree is not before.tree
    assert before.tree.body[0].value.id == 'first'
    assert after.tree.body[0].value.id == 'other'


def test_deleted_and_removed_files_cannot_reuse_cached_ast(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('value = 1\n', encoding='utf-8')
    store = SourceStore()
    original = store.snapshot([str(path)], FLOW_SOURCE)
    path.unlink()
    missing = store.snapshot([str(path)], FLOW_SOURCE).documents[str(path)]
    assert isinstance(missing.error, OSError) and missing.error_stage == 'read'
    assert missing.tree is None
    assert store.snapshot([], FLOW_SOURCE).documents == {}
    assert original.documents[str(path)].tree is not None


def test_cache_recovers_from_syntax_error_and_preserves_old_error_snapshot(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('def broken(: pass\n', encoding='utf-8')
    store = SourceStore()
    before = store.snapshot([str(path)], FLOW_SOURCE).documents[str(path)]
    path.write_text('def entry(value): return value\n', encoding='utf-8')
    after = store.snapshot([str(path)], FLOW_SOURCE).documents[str(path)]
    assert after.error is None and after.tree.body[0].name == 'entry'
    assert isinstance(before.error, SyntaxError) and before.tree is None


def test_new_snapshot_rereads_content_but_does_not_reparse_unchanged_source(monkeypatch):
    import pcresolve.frontend.source_snapshot as snapshots
    path = str(ROOT / 'pkg/helpers.py')
    parser = snapshots.ast.parse
    calls = []

    def parse(text):
        calls.append(text)
        return parser(text)

    monkeypatch.setattr(snapshots.ast, 'parse', parse)
    store = SourceStore()
    store.snapshot([path], FLOW_SOURCE)
    store.snapshot([path], OWNERSHIP_SOURCE)
    assert len(calls) == 1


def test_syntax_encoding_and_bom_policy_are_preserved(tmp_path):
    syntax = tmp_path / 'syntax.py'
    encoding = tmp_path / 'encoding.py'
    bom = tmp_path / 'bom.py'
    syntax.write_text('def broken(:\n    pass\n', encoding='utf-8')
    encoding.write_bytes(b'value = "\xff"\n')
    bom.write_bytes(b'\xef\xbb\xbfvalue = 1\n')
    files = [str(p) for p in (syntax, encoding, bom)]
    store = SourceStore()
    owner = store.snapshot(files, OWNERSHIP_SOURCE)
    flow = store.snapshot(files, FLOW_SOURCE)
    assert isinstance(owner.documents[str(syntax)].error, SyntaxError)
    assert owner.documents[str(syntax)].error_stage == 'parse'
    assert isinstance(owner.documents[str(encoding)].error, UnicodeDecodeError)
    assert owner.documents[str(encoding)].error_stage == 'read'
    assert isinstance(owner.documents[str(bom)].error, SyntaxError)
    assert flow.documents[str(bom)].error is None


@pytest.mark.parametrize('relative, owner, flow', [
    ('__init__.py', '', '__init__'), ('pkg/__init__.py', 'pkg', 'pkg'),
    ('pkg/contracts.py', 'pkg.contracts', 'pkg.contracts'),
    ('pkg/contracts.pyi', 'pkg.contractsi', 'pkg.contracts'),
    ('pkg/__init__.pyi', 'pkg.__init__i', 'pkg')])
def test_module_naming_preserves_existing_consumer_differences(relative, owner, flow):
    path = str(ROOT / relative)
    assert module_name_for_path(path, [str(ROOT)], OWNERSHIP_MODULES) == owner
    assert module_name_for_path(path, [str(ROOT)], FLOW_MODULES) == flow


def test_import_root_order_and_fallback_do_not_expand_source_set():
    path = str(ROOT / 'pkg/helpers.py')
    assert module_name_for_path(path, [str(ROOT.parent), str(ROOT)], FLOW_MODULES) == 'source_snapshot.pkg.helpers'
    assert module_name_for_path(path, [], FLOW_MODULES) == 'helpers'
    index = ModuleIndex.build([path], [str(ROOT)], FLOW_MODULES)
    assert tuple(index.file_to_module) == (path,)
    assert 'pkg.main' not in index.module_to_file


def test_flow_module_names_skip_roots_on_another_drive(monkeypatch):
    path = str(ROOT / 'pkg/helpers.py')
    unrelated_root = 'different-drive'
    commonpath = os.path.commonpath

    def cross_drive(paths):
        if paths[0] == unrelated_root:
            raise ValueError("Paths don't have the same drive")
        return commonpath(paths)

    monkeypatch.setattr(os.path, 'commonpath', cross_drive)
    assert module_name_for_path(path, [unrelated_root, str(ROOT)], FLOW_MODULES) == 'pkg.helpers'
    assert module_name_for_path(path, [unrelated_root], FLOW_MODULES) == 'helpers'


def test_module_index_retains_duplicate_candidates_and_existing_last_file_winner():
    files = [str(ROOT / 'pkg/contracts.py'), str(ROOT / 'pkg/contracts.pyi')]
    index = ModuleIndex.build(files, [str(ROOT)], FLOW_MODULES)
    assert [entry.module_name for entry in index.entries] == ['pkg.contracts', 'pkg.contracts']
    assert index.module_to_file['pkg.contracts'] == files[1]
    assert index.file_to_module[files[0]] == 'pkg.contracts'
    assert index.file_to_module[files[1]] == 'pkg.contracts'
    with pytest.raises(TypeError):
        index.module_to_file['pkg.contracts'] = files[0]


def test_module_mapper_uses_shared_index_without_changing_package_or_clear_behavior():
    mapper = ModuleMapper(str(ROOT))
    mapper.scan_project()
    assert mapper._index.file_to_module == mapper.file_to_module
    assert mapper.is_package('pkg')
    assert mapper.get_module_path(str(ROOT / '__init__.py')) == ''
    assert mapper.get_module_path(str(ROOT / 'pkg/contracts.pyi')) == 'pkg.contractsi'
    mapper.clear()
    assert not mapper._index.entries and mapper.get_all_modules() == []


def test_analyzers_consume_shared_snapshots_without_mutating_ast_or_public_results():
    store = SourceStore()
    owner = ProjectAnalyzer(str(ROOT))
    flow = FlowAnalyzer(project_root=ROOT)
    # Internal store injection exercises reuse without adding a public constructor option.
    owner._source_store = flow._source_store = store
    ownership = owner.analyze()
    before = owner._source_snapshot.documents[str(ROOT / 'pkg/main.py')]
    tree = ast.dump(before.tree, include_attributes=True)
    result = flow.analyze(FunctionRef(module='pkg.main', qualname='entry'), max_depth=2)
    after = flow._source_snapshot.documents[str(ROOT / 'pkg/main.py')]
    assert before.tree is after.tree and ast.dump(after.tree, include_attributes=True) == tree
    assert flow._module_index.file_to_module[str(ROOT / 'pkg/main.py')] == 'pkg.main'
    assert flow.analyze(result.entry, max_depth=2).to_dict() == result.to_dict()
    assert result.trace_parameter('value')['return_paths']
    assert {call.top_library for call in ownership.all_api_calls if call.func_name == 'identity'} == {'local'}
    assert {call.top_library for call in ownership.all_api_calls if call.func_name == 'json.loads'} == {'json'}
    assert '_source_snapshot' not in result.to_dict()


def test_flow_refreshes_cached_source_and_rejects_expansion_of_old_results(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('def helper(value): return value\ndef entry(value): return helper(value)\n', encoding='utf-8')
    flow = FlowAnalyzer(project_root=tmp_path)
    result = flow.analyze(FunctionRef(module='main', qualname='entry'))
    path.write_text('def helper(value): return None\ndef entry(value): return helper(value)\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Sources changed'):
        flow.expand(result, result.calls[0].id)
    current = flow.analyze(result.entry, max_depth=2)
    assert current.inputs['sha256'] != result.inputs['sha256']
    assert not current.trace_parameter('value')['return_paths']


def test_ownership_diagnostics_and_flow_boundaries_keep_existing_bom_behavior(tmp_path):
    (tmp_path / 'main.py').write_text('def entry(value): return value\n', encoding='utf-8')
    (tmp_path / 'bom.py').write_bytes(b'\xef\xbb\xbfvalue = 1\n')
    ownership = ProjectAnalyzer(str(tmp_path)).analyze()
    assert ownership.stats == {'total_modules': 2, 'parsed_modules': 1, 'skipped_modules': 1}
    assert ownership.diagnostics[0].code == 'SYNTAX_ERROR'
    flow = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef(module='main', qualname='entry'))
    assert not flow.boundaries
    assert len(flow.inputs['sha256']) == 2
