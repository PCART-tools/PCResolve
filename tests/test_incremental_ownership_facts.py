## @package tests.test_incremental_ownership_facts
#  Reused visitor facts are pristine and detached from mutable analysis state.

from pathlib import Path
import ast
import gc
import os
import weakref

import pytest

from pcresolve import ProjectAnalyzer
from pcresolve.ownership.collect.single_file import SingleFileAnalyzer
from pcresolve.ownership.source_fact_cache import SingleFileFacts, capture_source_facts, clone_source_facts
from pcresolve.frontend.source_snapshot import SourceDocument
from pcresolve.ownership.views import build_full_view


@pytest.mark.parametrize('fixture', ['indexed_callable_dispatch', 'branch_callable_field',
                                    'local_classmethod_factory', 'factory_resolved_func'])
def test_reused_visitor_facts_equal_fresh_analysis(fixture):
    root = Path(__file__).parent / 'fixtures' / fixture
    if not root.exists():
        pytest.fail('missing fixture ' + fixture)
    analyzer = ProjectAnalyzer(str(root), reuse_source_facts=True)
    before = build_full_view(analyzer.analyze())
    after = build_full_view(analyzer.analyze())
    assert before == after == build_full_view(ProjectAnalyzer(str(root)).analyze())
    assert analyzer._ownership_run.source_facts_reused > 0


def test_cached_facts_detach_collector_closures_and_isolate_clone_notifications():
    tree = ast.parse('class Factory:\n def build(self): return 1\n')
    document = SourceDocument('main.py', tree=tree)

    def make_collector():
        collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
        collector.visit(tree)
        collector.module_cg.transient_callback = lambda: collector
        collector.call_site_objects.append(
            {'items': [collector.module_cg, lambda: collector]})
        collector.unclassified_extension = lambda: collector
        return collector

    collector = make_collector()
    original = weakref.ref(collector)
    facts = capture_source_facts(collector, document)
    assert any(is_root for _, is_root, _ in facts.versioned_edges)
    assert all(owner is None for _, is_root, owner in facts.versioned_edges if is_root)
    del collector
    gc.collect()
    assert original() is None
    left = clone_source_facts(facts, document)
    right = clone_source_facts(facts, document)
    assert left.module_cg.transient_callback is None
    assert right.module_cg.transient_callback is None
    assert left.call_site_objects[0]['items'][0] is left.module_cg
    assert left.call_site_objects[0]['items'][1] is None
    assert right.call_site_objects[0]['items'][0] is right.module_cg
    assert not hasattr(left, 'unclassified_extension')
    left_version, right_version = left.version, right.version
    left.module_cg.functions['probe'] = object()
    assert left.version > left_version
    assert right.version == right_version
    assert 'probe' not in right.module_cg.functions


def test_file_edit_revisits_only_changed_module_and_does_not_reuse_query_state(tmp_path, monkeypatch):
    main = tmp_path / 'main.py'
    helper = tmp_path / 'helper.py'
    main.write_text('import json\nfrom helper import invoke\ninvoke(json.loads)\n', encoding='utf-8')
    helper.write_text('def invoke(api): return api("{}")\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    old = analyzer.analyze()
    old.all_api_calls[0].top_library = 'corrupted'
    visited = []
    original = SingleFileAnalyzer.visit_Module
    def record(self, node):
        visited.append(self.module_name)
        return original(self, node)
    monkeypatch.setattr(SingleFileAnalyzer, 'visit_Module', record)
    stat = helper.stat()
    helper.write_text('def invoke(api): return str("{}")\n', encoding='utf-8')
    os.utime(helper, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert helper.stat().st_size == stat.st_size
    current = analyzer.analyze()
    assert visited == ['helper']
    assert analyzer._ownership_run.source_facts_reused == 1
    assert build_full_view(current) == build_full_view(ProjectAnalyzer(str(tmp_path)).analyze())
    cached = analyzer._source_fact_cache[str(main)][-1]
    assert isinstance(cached, SingleFileFacts)
    assert not hasattr(cached, '_mapping_facts')
    live = analyzer._ownership_run.program.module_tracers['main']
    assert live._mapping_facts.lookup.__self__ is live
    assert live.symbols.direct is not cached.visitor.symbols.direct
    assert live.module_cg is not cached.visitor.module_cg
    version = live.version
    live.module_cg.functions['__cache_listener_probe__'] = object()
    assert live.version > version


def test_syntax_failure_and_recovery_drop_stale_visitor_facts(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('print(1)\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    before = build_full_view(analyzer.analyze())
    path.write_text('def broken(:\n', encoding='utf-8')
    assert analyzer.analyze().diagnostics
    assert not analyzer._source_fact_cache
    path.write_text('print(1)\n', encoding='utf-8')
    assert build_full_view(analyzer.analyze()) == before


def test_deleted_module_is_removed_from_mapping_and_fact_cache(tmp_path):
    main = tmp_path / 'main.py'
    provider = tmp_path / 'provider.py'
    main.write_text('import provider\nprovider.invoke()\n', encoding='utf-8')
    provider.write_text('def invoke(): pass\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    analyzer.analyze()
    provider.unlink()
    current = analyzer.analyze()
    assert 'provider' not in analyzer.module_mapper.get_all_modules()
    assert str(provider) not in analyzer._source_fact_cache
    assert build_full_view(current) == build_full_view(ProjectAnalyzer(str(tmp_path)).analyze())


def test_local_module_lookup_uses_live_mapping_without_list_copy(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text('print(1)\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    def reject_list():
        pytest.fail('local membership must not copy the module list')
    monkeypatch.setattr(analyzer.module_mapper, 'get_all_modules', reject_list)
    assert analyzer.is_local('main')
    analyzer.module_mapper.module_to_file.clear()
    assert not analyzer.is_local('main')
    assert not analyzer.is_local([])
