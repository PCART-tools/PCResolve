## @package tests.test_incremental_ownership_facts
#  Reused visitor facts are pristine and detached from mutable analysis state.

from pathlib import Path
import ast
import gc
import os
import weakref
from functools import partial

import pytest

from pcresolve import ProjectAnalyzer
from pcresolve.ownership.collect.single_file import SingleFileAnalyzer
from pcresolve.ownership.source_fact_cache import SingleFileFacts, capture_source_facts, clone_source_facts
from pcresolve.ownership.ir import CallSite, SymbolRef
from pcresolve.frontend.source_snapshot import SourceDocument
from pcresolve.ownership.views import build_full_view
from pcresolve.runtime.limits import AnalysisBudget, AnalysisLimitExceeded, AnalysisLimits
import pcresolve.ownership.analyzer as analyzer_module
import pcresolve.ownership.source_fact_cache as cache_module


_callback_global_values = []
_callback_global_constant = ('stable', 1)


def _append_callback_global(value):
    _callback_global_values.append(value)


def _pure_recursive_callback(value):
    return _pure_recursive_callback(value - 1) if value else 'done'


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


@pytest.mark.parametrize('kind', ['container', 'default', 'keyword_default', 'nested',
                                  'partial', 'partial_attribute', 'slotted', 'container_attribute'])
def test_cached_callbacks_do_not_indirectly_retain_collector(kind):
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)

    def capture():
        collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
        collector.visit(tree)
        if kind == 'container':
            box = [collector]
            def callback():
                return box[0]
        elif kind == 'default':
            def callback(value=collector):
                return value
        elif kind == 'keyword_default':
            def callback(*, value=collector):
                return value
        elif kind == 'nested':
            def inner():
                return collector
            def callback():
                return inner()
        elif kind == 'partial_attribute':
            callback = partial(lambda: None)
            callback.owner = collector
        elif kind == 'slotted':
            class Box:
                __slots__ = ('value',)
            box = Box()
            box.value = collector
            def callback():
                return box.value
        elif kind == 'container_attribute':
            class Box(list):
                pass
            box = Box()
            box.owner = collector
            def callback():
                return box.owner
        else:
            callback = partial(lambda value: value, collector)
        collector.module_cg.transient_callback = callback
        return weakref.ref(collector), capture_source_facts(collector, document)

    collector_ref, facts = capture()
    gc.collect()
    assert collector_ref() is None
    assert facts.visitor.module_cg.transient_callback is None
    assert clone_source_facts(facts, document).module_cg.transient_callback is None


@pytest.mark.parametrize('holder_kind', ['slots', 'dict_subclass', 'list_subclass'])
def test_callback_inside_fact_object_does_not_retain_collector(holder_kind):
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)

    class Holder:
        __slots__ = ('callback',)

    class DictHolder(dict):
        pass

    class ListHolder(list):
        pass

    def capture():
        collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
        collector.visit(tree)
        holder = {'slots': Holder, 'dict_subclass': DictHolder,
                  'list_subclass': ListHolder}[holder_kind]()
        holder.callback = lambda: collector
        collector.module_cg.transient_holder = holder
        return weakref.ref(collector), capture_source_facts(collector, document)

    reference, facts = capture()
    gc.collect()
    assert reference() is None
    assert facts.visitor.module_cg.transient_holder.callback is None
    assert clone_source_facts(facts, document).module_cg.transient_holder.callback is None


def test_cache_rejects_direct_collector_reference_in_fact():
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    collector.module_cg.transient_owner = {'owner': collector}
    with pytest.raises(ValueError, match='source facts reference their collector'):
        capture_source_facts(collector, document)
    assert collector.module_cg.transient_owner['owner'] is collector
    del collector.module_cg.transient_owner
    assert clone_source_facts(capture_source_facts(collector, document), document)._module_tree is tree


@pytest.mark.parametrize('kind', ['closure', 'default', 'nested', 'partial'])
def test_callback_closure_with_mutable_state_is_detached_from_cache_clones(kind):
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    def make_callback():
        values = []
        def inner(value):
            values.append(value)
            return list(values)
        if kind == 'default':
            def callback(value, target=values):
                target.append(value)
                return list(target)
        elif kind == 'nested':
            def callback(value):
                return inner(value)
        elif kind == 'partial':
            callback = partial(inner)
        else:
            callback = inner
        return callback
    collector.module_cg.transient_callback = make_callback()
    facts = capture_source_facts(collector, document)
    left = clone_source_facts(facts, document)
    right = clone_source_facts(facts, document)
    assert left.module_cg.transient_callback is None
    assert right.module_cg.transient_callback is None
    assert facts.visitor.module_cg.transient_callback is None
    assert collector.module_cg.transient_callback('original') == ['original']


def test_callback_with_immutable_closure_is_not_cached():
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    def make_callback():
        prefix = ('stable', 1)
        return lambda value: (prefix, value)
    collector.module_cg.transient_callback = make_callback()
    facts = capture_source_facts(collector, document)
    assert facts.visitor.module_cg.transient_callback is None
    assert clone_source_facts(facts, document).module_cg.transient_callback is None
    assert collector.module_cg.transient_callback('x') == (('stable', 1), 'x')


@pytest.mark.parametrize('wrapped', [False, True])
def test_callback_using_mutable_global_is_detached_from_cached_clones(wrapped):
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    def callback(value):
        _callback_global_values.append(value)
    original = partial(callback) if wrapped else callback
    collector.module_cg.transient_callback = original
    facts = capture_source_facts(collector, document)
    left = clone_source_facts(facts, document)
    right = clone_source_facts(facts, document)
    assert facts.visitor.module_cg.transient_callback is None
    assert left.module_cg.transient_callback is None
    assert right.module_cg.transient_callback is None
    assert collector.module_cg.transient_callback is original


def test_callback_using_immutable_global_is_not_cached():
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    def callback():
        return _callback_global_constant
    collector.module_cg.transient_callback = callback
    facts = capture_source_facts(collector, document)
    assert facts.visitor.module_cg.transient_callback is None
    assert clone_source_facts(facts, document).module_cg.transient_callback is None
    assert collector.module_cg.transient_callback() == ('stable', 1)


def test_callback_using_global_helper_with_mutable_state_is_detached():
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    def callback(value):
        _append_callback_global(value)
    collector.module_cg.transient_callback = callback
    facts = capture_source_facts(collector, document)
    assert facts.visitor.module_cg.transient_callback is None
    assert clone_source_facts(facts, document).module_cg.transient_callback is None
    assert collector.module_cg.transient_callback is callback


def test_callback_using_recursive_global_helper_is_not_cached():
    tree = ast.parse('x = 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    def callback(value):
        return _pure_recursive_callback(value)
    collector.module_cg.transient_callback = callback
    facts = capture_source_facts(collector, document)
    assert facts.visitor.module_cg.transient_callback is None
    assert clone_source_facts(facts, document).module_cg.transient_callback is None
    assert collector.module_cg.transient_callback(2) == 'done'


def test_project_rejects_collector_reference_without_publishing_partial_cache(tmp_path, monkeypatch):
    stable = tmp_path / 'stable.py'
    changed = tmp_path / 'changed.py'
    stable.write_text('import json\njson.loads("{}")\n', encoding='utf-8')
    changed.write_text('import json\njson.loads("{}")\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    analyzer.analyze()
    old_cache = analyzer._source_fact_cache
    old_entries = dict(old_cache)
    changed.write_text('import json\njson.dumps({})\n', encoding='utf-8')

    original_visit = SingleFileAnalyzer.visit_Module
    def visit_with_invalid_fact(self, node):
        result = original_visit(self, node)
        if self.module_name == 'changed':
            self.module_cg.transient_owner = {'owner': self}
        return result

    with monkeypatch.context() as patch:
        patch.setattr(SingleFileAnalyzer, 'visit_Module', visit_with_invalid_fact)
        with pytest.raises(ValueError, match='source facts reference their collector'):
            analyzer.analyze()
    assert analyzer._source_fact_cache is old_cache
    assert analyzer._source_fact_cache == old_entries
    actual = build_full_view(analyzer.analyze())
    expected = build_full_view(ProjectAnalyzer(str(tmp_path), reuse_source_facts=False).analyze())
    assert actual == expected
    assert analyzer._source_fact_cache[str(stable)] is old_entries[str(stable)]
    assert analyzer._source_fact_cache[str(changed)] is not old_entries[str(changed)]


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


@pytest.mark.parametrize('failure_site', ['capture', 'clone', 'propagation'])
def test_failed_run_preserves_published_cache_and_recovers(tmp_path, monkeypatch, failure_site):
    path = tmp_path / 'main.py'
    path.write_text('import json\njson.loads("{}")\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    analyzer.analyze()
    previous_cache = analyzer._source_fact_cache
    if failure_site == 'capture':
        path.write_text('import json\njson.dumps({})\n', encoding='utf-8')
    def fail(*args, **kwargs):
        raise RuntimeError('injected failure')
    with monkeypatch.context() as patch:
        if failure_site == 'propagation':
            patch.setattr(analyzer, '_bind_bounded_local_call_results', fail)
        else:
            patch.setattr(analyzer_module, failure_site + '_source_facts', fail)
        with pytest.raises(RuntimeError, match='injected failure'):
            analyzer.analyze()
    assert analyzer._source_fact_cache is previous_cache
    if failure_site == 'propagation':
        assert all(not tracer._ownership_import_unstable
                   for tracer in analyzer._ownership_run.program.module_tracers.values())
    assert build_full_view(analyzer.analyze()) == build_full_view(
        ProjectAnalyzer(str(tmp_path)).analyze())


def test_capture_receives_current_run_budget(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text('print(1)\n', encoding='utf-8')
    original = analyzer_module.capture_source_facts
    observed = []
    def capture(tracer, document, budget):
        observed.append(budget)
        return original(tracer, document, budget)
    monkeypatch.setattr(analyzer_module, 'capture_source_facts', capture)
    analyzer = ProjectAnalyzer(str(tmp_path), analysis_limits=AnalysisLimits(max_work=100000),
                               reuse_source_facts=True)
    analyzer.analyze()
    assert observed == [analyzer._analysis_budget]


def test_cache_entry_requires_same_document_and_import_context(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('print(1)\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    analyzer.analyze()
    entry = analyzer._source_fact_cache[str(path)]
    document = entry.document
    assert entry.matches(document, 'main', False)
    assert not entry.matches(SourceDocument(document.file_path, tree=document.tree), 'main', False)
    assert not entry.matches(document, 'other', False)
    assert not entry.matches(document, 'main', True)
    find = cache_module.find_source_fact_entry
    assert find(analyzer._source_fact_cache, str(path), document, 'main', False) is entry
    assert find(analyzer._source_fact_cache, 'other.py', document, 'main', False) is None
    assert find(analyzer._source_fact_cache, str(path), document, 'other', False) is None
    assert find(analyzer._source_fact_cache, str(path), document, 'main', True) is None
    assert find(analyzer._source_fact_cache, str(path), SourceDocument(str(path), tree=document.tree),
                'main', False) is None


@pytest.mark.parametrize('operation', ['capture', 'clone'])
def test_internal_cache_failure_does_not_damage_existing_graphs(operation, monkeypatch):
    tree = ast.parse('class Factory:\n def build(self): return 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    original_callback = collector.module_cg.functions._changed
    facts = capture_source_facts(collector, document)
    other = clone_source_facts(facts, document)
    name = '_detach_fact_callbacks' if operation == 'capture' else '_reattach_fact_callbacks'
    original = getattr(cache_module, name)

    def fail_after_mutation(*args):
        original(*args)
        raise RuntimeError('injected after callback mutation')

    with monkeypatch.context() as patch:
        patch.setattr(cache_module, name, fail_after_mutation)
        with pytest.raises(RuntimeError, match='after callback mutation'):
            if operation == 'capture':
                capture_source_facts(collector, document)
            else:
                clone_source_facts(facts, document)
    fresh = clone_source_facts(facts, document)
    other_version, fresh_version = other.version, fresh.version
    collector.module_cg.functions['collector-only'] = object()
    other.module_cg.functions['other-only'] = object()
    assert collector.module_cg.functions._changed == original_callback
    assert other.version > other_version
    assert fresh.version == fresh_version
    assert 'collector-only' not in facts.visitor.module_cg.functions
    assert 'other-only' not in facts.visitor.module_cg.functions
    assert 'other-only' not in fresh.module_cg.functions


@pytest.mark.parametrize('operation', ['capture', 'clone'])
def test_budget_exit_during_ast_memo_keeps_facts_reusable(operation):
    tree = ast.parse('class Factory:\n def build(self): return 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    facts = capture_source_facts(collector, document)
    budget = AnalysisBudget(AnalysisLimits(max_work=3))
    with pytest.raises(AnalysisLimitExceeded, match='work limit'):
        if operation == 'capture':
            capture_source_facts(collector, document, budget)
        else:
            clone_source_facts(facts, document, budget)
    fresh = clone_source_facts(facts, document)
    version = fresh.version
    fresh.module_cg.functions['probe'] = object()
    assert fresh.version > version
    assert 'probe' not in facts.visitor.module_cg.functions


def test_capture_budget_stops_during_fact_graph_traversal(monkeypatch):
    tree = ast.parse('class Factory:\n def build(self): return 1\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    original_callback = collector.module_cg.functions._changed
    reached_graph = []
    original = cache_module._detach_visitor_callbacks

    def tracking_detach(values, tracer, memo, budget):
        reached_graph.append(True)
        return original(values, tracer, memo, budget)

    monkeypatch.setattr(cache_module, '_detach_visitor_callbacks', tracking_detach)
    budget = AnalysisBudget(AnalysisLimits(max_work=1 + sum(1 for _ in ast.walk(tree))))
    with pytest.raises(AnalysisLimitExceeded, match='work limit'):
        capture_source_facts(collector, document, budget)
    assert reached_graph == [True]
    assert collector.module_cg.functions._changed == original_callback
    facts = capture_source_facts(collector, document)
    clone = clone_source_facts(facts, document)
    version = clone.version
    clone.module_cg.functions['probe'] = object()
    assert clone.version > version
    assert 'probe' not in facts.visitor.module_cg.functions


def test_clone_rejects_facts_from_another_source_generation():
    tree = ast.parse('print(1)\n')
    original = SourceDocument('main.py', tree=tree)
    replacement = SourceDocument('main.py', tree=ast.parse('print(2)\n'))
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    with pytest.raises(ValueError, match='different source document'):
        capture_source_facts(collector, replacement)
    facts = capture_source_facts(collector, original)
    assert facts.document is original
    with pytest.raises(ValueError, match='different source document'):
        clone_source_facts(facts, replacement)
    assert clone_source_facts(facts, original)._module_tree is tree


def test_inconsistent_cache_entry_never_reuses_other_generation(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('print(1)\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    analyzer.analyze()
    old_entry = analyzer._source_fact_cache[str(path)]
    path.write_text('print(2)\n', encoding='utf-8')
    analyzer.analyze()
    current_entry = analyzer._source_fact_cache[str(path)]
    corrupted = current_entry._replace(facts=old_entry.facts)
    analyzer._source_fact_cache[str(path)] = corrupted
    with pytest.raises(ValueError, match='different source document'):
        analyzer.analyze()
    assert analyzer._source_fact_cache[str(path)] is corrupted
    analyzer._source_fact_cache[str(path)] = current_entry
    assert build_full_view(analyzer.analyze()) == build_full_view(
        ProjectAnalyzer(str(tmp_path)).analyze())


def test_parameter_lookup_index_is_rebuilt_per_clone():
    tree = ast.parse('def original(argument):\n    return argument\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    expected = collector._parameter_definitions('argument')
    assert expected and collector._parameter_name_index is not None
    facts = capture_source_facts(collector, document)
    assert not hasattr(facts.visitor, '_parameter_name_index')
    first = clone_source_facts(facts, document)
    second = clone_source_facts(facts, document)
    assert first._parameter_name_index is None
    assert second._parameter_name_index is None
    first.function_params['added'] = ['argument']
    assert ('added', 0) in first._parameter_definitions('argument')
    assert second._parameter_definitions('argument') == expected
    assert first._parameter_name_index is not second._parameter_name_index


def test_cloned_scope_aliases_and_binding_order_remain_run_local():
    tree = ast.parse('import json\nvalue = json.loads("{}")\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    facts = capture_source_facts(collector, document)
    first = clone_source_facts(facts, document)
    second = clone_source_facts(facts, document)
    assert first.scope_stack[0] is first.module_scope
    assert second.scope_stack[0] is second.module_scope
    assert facts.visitor.scope_stack[0] is facts.visitor.module_scope
    assert first.module_scope is not second.module_scope
    previous_counter = first._assignment_counter
    assert second._assignment_counter == previous_counter
    first._bind_target_name('new_local', 'external.source')
    assert first._assignment_counter == previous_counter + 1
    assert first.current_scope().lookup('new_local') is not None
    assert second._assignment_counter == previous_counter
    assert second.current_scope().lookup('new_local') is None
    assert facts.visitor.module_scope.lookup('new_local') is None
    assert 'new_local' not in second.symbols.direct


def test_cloned_mapping_origins_and_symbol_return_aliases_are_isolated():
    tree = ast.parse('def target(): pass\nregistry = {"run": target}\nregistry["run"]()\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    facts = capture_source_facts(collector, document)
    first = clone_source_facts(facts, document)
    second = clone_source_facts(facts, document)
    node = next(node for node in ast.walk(tree) if isinstance(node, ast.Subscript))
    first_selected = first._mapping_facts.value(node)
    second_selected = second._mapping_facts.value(node)
    assert first_selected.targets()[1] and second_selected.targets()[1]
    assert first.symbols.return_sources is first.return_sources
    assert second.symbols.return_sources is second.return_sources
    assert facts.visitor.symbols.return_sources is facts.visitor.return_sources
    first._mapping_facts.invalidate(first._mapping_facts.value(ast.Name(id='registry', ctx=ast.Load())))
    first.return_sources['probe'] = 'external'
    assert first_selected.targets() == ((), False)
    assert second_selected.targets()[1]
    assert 'probe' not in second.symbols.return_sources
    assert 'probe' not in facts.visitor.symbols.return_sources
    third = clone_source_facts(facts, document)
    assert third._mapping_facts.value(node).targets()[1]


def test_cached_record_types_follow_real_collector_and_clone():
    tree = ast.parse('import json\ndef use(): return json.loads("{}")\nuse()\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    facts = capture_source_facts(collector, document)
    clone = clone_source_facts(facts, document)
    for state in (facts.visitor, clone):
        assert state.symbol_refs and all(isinstance(item, SymbolRef) for item in state.symbol_refs)
        assert state.call_site_objects and all(isinstance(item, CallSite) for item in state.call_site_objects)
        assert state.api_calls and all(isinstance(item, dict) for item in state.api_calls)
        assert all(isinstance(item, dict) for item in state.attr_accesses)
        assert all(isinstance(item, str) for item in state.local | state.defined_functions | state.import_aliases)


def test_collector_temporary_call_targets_and_namespace_cache_are_run_local():
    tree = ast.parse('import pkg\nvalue = pkg.load()\n')
    document = SourceDocument('main.py', tree=tree)
    collector = SingleFileAnalyzer(module_name='main', file_path='main.py')
    collector.visit(tree)
    collector._pending_call_targets_by_node[123] = ['temporary']
    expected = collector._finite_namespace_is_stable('pkg')
    assert 'pkg' in collector._finite_namespace_stability
    facts = capture_source_facts(collector, document)
    assert not hasattr(facts.visitor, '_pending_call_targets_by_node')
    assert not hasattr(facts.visitor, '_finite_namespace_stability')
    first = clone_source_facts(facts, document)
    second = clone_source_facts(facts, document)
    assert not first._pending_call_targets_by_node
    assert not first._finite_namespace_stability
    assert first._finite_namespace_is_stable('pkg') == expected
    assert not second._finite_namespace_stability
    assert second._finite_namespace_is_stable('pkg') == expected
    assert first._finite_namespace_stability is not second._finite_namespace_stability


def test_project_budget_failure_during_capture_preserves_old_cache_and_recovers(tmp_path, monkeypatch):
    path = tmp_path / 'main.py'
    path.write_text('import json\njson.loads("{}")\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    analyzer.analyze()
    previous = analyzer._source_fact_cache
    old_entry = previous[str(path)]
    path.write_text('import json\njson.dumps({})\n', encoding='utf-8')
    analyzer.analysis_limits = AnalysisLimits(max_work=100000)
    original = cache_module._detach_visitor_callbacks
    reached = []

    def exhaust_during_capture(values, tracer, memo, budget):
        reached.append(True)
        assert budget is analyzer._analysis_budget
        budget.checkpoint(work=budget.limits.max_work + 1)
        return original(values, tracer, memo, budget)

    with monkeypatch.context() as patch:
        patch.setattr(cache_module, '_detach_visitor_callbacks', exhaust_during_capture)
        with pytest.raises(AnalysisLimitExceeded, match='work'):
            analyzer.analyze()
    assert reached == [True]
    assert analyzer._source_fact_cache is previous
    assert analyzer._source_fact_cache[str(path)] is old_entry
    analyzer.analysis_limits = None
    assert build_full_view(analyzer.analyze()) == build_full_view(
        ProjectAnalyzer(str(tmp_path)).analyze())
    assert analyzer._source_fact_cache[str(path)] is not old_entry


def test_cold_cached_changed_and_restored_source_match_fresh_analysis(tmp_path):
    path = tmp_path / 'main.py'
    original = 'import json\njson.loads("{}")\n'
    changed = 'import json\njson.dumps({})\n'
    path.write_text(original, encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)

    def verify():
        actual = build_full_view(analyzer.analyze())
        uncached = build_full_view(ProjectAnalyzer(str(tmp_path), reuse_source_facts=False).analyze())
        assert actual == uncached
        return actual

    cold = verify()
    assert verify() == cold
    assert analyzer._ownership_run.source_facts_reused == 1
    path.write_text(changed, encoding='utf-8')
    edited = verify()
    assert edited != cold
    assert analyzer._ownership_run.source_facts_reused == 0
    path.write_text(original, encoding='utf-8')
    assert verify() == cold
    assert analyzer._ownership_run.source_facts_reused == 0


@pytest.mark.parametrize(('field', 'value'), [
    ('file_path', 'different.py'),
    ('module_name', 'different'),
    ('is_package', True),
])
def test_inconsistent_inner_cache_context_is_rejected(tmp_path, field, value):
    path = tmp_path / 'main.py'
    path.write_text('import json\njson.loads("{}")\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path), reuse_source_facts=True)
    expected = build_full_view(analyzer.analyze())
    valid = analyzer._source_fact_cache[str(path)]
    corrupted = valid._replace(facts=valid.facts._replace(**{field: value}))
    analyzer._source_fact_cache[str(path)] = corrupted
    with pytest.raises(ValueError, match='inconsistent module context'):
        analyzer.analyze()
    assert analyzer._source_fact_cache[str(path)] is corrupted
    analyzer._source_fact_cache[str(path)] = valid
    assert build_full_view(analyzer.analyze()) == expected
