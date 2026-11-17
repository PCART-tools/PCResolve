## @package tests.test_performance_fact_indexes
#  Indexed lookups retain conservative answers across mutable fact generations.

import ast
import gc
import weakref
from dataclasses import replace

import pytest

from pcresolve import ProjectAnalyzer
from pcresolve.ownership.analyzer import _is_import_origin
from pcresolve.ownership.ir import SymbolRef
from pcresolve.ownership.collect.single_file import SingleFileAnalyzer
from pcresolve.ownership.call_graph import ProjectCallGraph
from pcresolve.ownership.ownership_model import build_ownership_definition_index
from pcresolve.ownership.sources import CallResult, SourceSet
from pcresolve.ownership.resolve.target_metadata import edge_callable_names
from pcresolve.ownership.sources import normalize_source


def project(tmp_path):
    (tmp_path / 'main.py').write_text(
        'class A:\n @classmethod\n def make(cls): return A()\n'
        'class B:\n @staticmethod\n def make(): return B()\n'
        'x = A.make()\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    return analyzer, analyzer._ownership_run.program.module_tracers


def test_method_candidates_are_indexed_and_read_live_returns(tmp_path):
    analyzer, tracers = project(tmp_path)
    query = CallResult('main.A.make')
    assert analyzer._local_class_from_method_result('main', query, tracers) == [('main', 'A')]
    indexed = analyzer._get_method_result_index()
    for _ in range(3):
        assert analyzer._get_method_result_index() is indexed
    tracers['main'].module_cg.classes['A'].methods['make'].returns = CallResult('B')
    assert analyzer._local_class_from_method_result('main', query, tracers) == [('main', 'B')]
    tracers['main'].module_cg.classes['A'].methods.clear()
    assert analyzer._local_class_from_method_result('main', query, tracers) == []
    assert analyzer._get_method_result_index() is not indexed


def test_definition_index_belongs_to_run_and_tracks_graph_identity_and_version(tmp_path):
    analyzer, tracers = project(tmp_path)
    run = analyzer._ownership_run
    first = analyzer._get_ownership_definition_index()
    assert run.definition_index is first
    assert analyzer._get_definition_index() is first.definitions
    assert analyzer._get_ownership_definition_index() is first
    assert first.target_names['make']
    tracers['main'].module_cg.functions.clear()
    changed = analyzer._get_ownership_definition_index()
    assert changed is run.definition_index and changed is not first
    assert changed.graph is analyzer.project_cg

    empty1, empty2 = ProjectCallGraph(), ProjectCallGraph()
    assert empty1.version == empty2.version
    analyzer.project_cg = empty1
    first_empty = analyzer._get_ownership_definition_index()
    analyzer.project_cg = empty2
    second_empty = analyzer._get_ownership_definition_index()
    assert first_empty is not second_empty
    assert second_empty.graph is empty2 and run.definition_index is second_empty


def test_definition_index_builder_rejects_missing_module_metadata(tmp_path):
    analyzer, _ = project(tmp_path)
    run = analyzer._ownership_run
    old_index = analyzer._get_ownership_definition_index()
    with pytest.raises(ValueError, match='definition module is missing'):
        build_ownership_definition_index(analyzer.project_cg, lambda module, name: None)
    assert run.definition_index is old_index
    assert analyzer._get_ownership_definition_index() is old_index


def test_actual_definition_index_builder_is_used_and_preserves_records(tmp_path, monkeypatch):
    analyzer, _ = project(tmp_path)
    import pcresolve.ownership.resolve.project_call_context as context
    original = context.build_ownership_definition_index
    observed = []
    def observe(graph, metadata):
        result = original(graph, metadata)
        observed.append((graph, metadata.__self__, result))
        return result
    monkeypatch.setattr(context, 'build_ownership_definition_index', observe)
    analyzer._ownership_run.definition_index = None
    index = analyzer._get_ownership_definition_index()
    assert observed == [(analyzer.project_cg, analyzer, index)]
    assert index.generation == analyzer.project_cg.version
    assert [record.qualname for record in index.definitions.records if record.kind == 'function'] == [
        'A.make', 'B.make']


def test_definition_index_build_during_graph_mutation_does_not_publish(tmp_path, monkeypatch):
    analyzer, tracers = project(tmp_path)
    old_index = analyzer._get_ownership_definition_index()
    tracers['main'].module_cg.edges.append(replace(tracers['main'].module_cg.edges[0]))
    original = analyzer._local_target_metadata
    modified = []
    def mutate_once(module, name):
        metadata = original(module, name)
        if not modified:
            tracers['main'].module_cg.edges.append(replace(tracers['main'].module_cg.edges[0]))
            modified.append(True)
        return metadata
    monkeypatch.setattr(analyzer, '_local_target_metadata', mutate_once)
    with pytest.raises(RuntimeError, match='call graph changed during definition indexing'):
        analyzer._get_ownership_definition_index()
    assert modified == [True]
    assert analyzer._ownership_run.definition_index is old_index
    second = analyzer._get_ownership_definition_index()
    assert second is not old_index and second.generation == analyzer.project_cg.version


def test_target_metadata_real_analyzer_uses_current_graph(tmp_path):
    (tmp_path / 'main.py').write_text(
        'class Item:\n'
        ' def __init__(self): pass\n'
        ' def process(self): pass\n'
        'def top(): pass\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    assert analyzer._local_target_metadata('main', 'Item.process') is None
    analyzer.analyze()
    module_graph = analyzer.project_cg.modules['main']
    assert analyzer._local_target_metadata('main', 'Item.__init__') == (
        module_graph, 'Item', '__init__', True, False)
    assert analyzer._local_target_metadata('main', 'Item.process') == (
        module_graph, 'Item', 'process', False, True)
    assert analyzer._local_target_metadata('main', 'top') == (
        module_graph, '', 'top', False, False)
    assert analyzer._local_target_metadata('other', 'top') is None
    del module_graph.classes['Item'].methods['process']
    assert analyzer._local_target_metadata('main', 'Item.process') == (
        module_graph, 'Item', 'process', False, False)


def test_method_index_belongs_to_run_and_releases_previous_graph(tmp_path):
    analyzer, tracers = project(tmp_path)
    first_run = analyzer._ownership_run
    first_graph = first_run.program.call_graph
    graph_ref = weakref.ref(first_graph)
    index = analyzer._get_method_result_index()
    assert first_run.method_result_index.data is index
    assert first_run.method_result_index.graph is first_graph
    del tracers, index, first_run, first_graph
    (tmp_path / 'main.py').write_text('value = 1\n', encoding='utf-8')
    analyzer.analyze()
    assert (analyzer._ownership_run.method_result_index is None
            or analyzer._ownership_run.method_result_index.graph is analyzer.project_cg)
    gc.collect()
    assert graph_ref() is None


def test_pre_run_method_index_does_not_survive_into_run(tmp_path):
    (tmp_path / 'main.py').write_text('value = 1\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    graph = ProjectCallGraph()
    graph_ref = weakref.ref(graph)
    analyzer.project_cg = graph
    analyzer._get_method_result_index()
    assert analyzer._initial_method_result_index.graph is graph
    analyzer.analyze()
    assert analyzer._initial_method_result_index is None
    del graph
    gc.collect()
    assert graph_ref() is None


def test_method_aliases_retain_existing_order_and_live_bindings(tmp_path):
    analyzer, tracers = project(tmp_path)
    tracer = tracers['main']
    tracer.import_from_symbols['Alias'] = 'main.A'
    # The legacy import-class rule accepts any tail; indexing must retain it.
    assert analyzer._local_class_from_method_result(
        'main', CallResult('Alias.other'), tracers) == [('main', 'A')]
    tracer.import_from_symbols['Alias'] = 'main.B'
    assert analyzer._local_class_from_method_result(
        'main', CallResult('Alias.other'), tracers) == [('main', 'B')]
    tracer.symbols.direct['mod'] = 'main'
    assert analyzer._local_class_from_method_result(
        'main', CallResult('mod.A.make'), tracers) == [('main', 'A')]


def test_edge_index_constant_cost_hit_and_structural_invalidation(tmp_path, monkeypatch):
    analyzer, tracers = project(tmp_path)
    indexed = analyzer._get_edge_lookup()
    assert analyzer._ownership_run.edge_index.data is indexed
    assert analyzer._ownership_run.edge_index.graph is analyzer.project_cg
    graph = analyzer.project_cg
    original_items = graph.modules.items
    def reject_scan():
        pytest.fail('a valid edge index must not scan every module')
    monkeypatch.setattr(graph.modules, 'items', reject_scan)
    assert analyzer._get_edge_lookup() is indexed
    monkeypatch.setattr(graph.modules, 'items', original_items)
    module = tracers['main'].module_cg
    added = replace(module.edges[0], call_lineno=1000)
    module.edges.append(added)
    assert any(edge is added for _, edge in analyzer._get_edge_lookup()[0])
    module.edges[:] = [added]
    assert analyzer._get_edge_lookup()[0] == [('main', added)]
    module.edges = []
    assert analyzer._get_edge_lookup()[0] == []
    graph.modules.clear()
    assert analyzer._get_edge_lookup()[0] == []


@pytest.mark.parametrize(('source', 'expected'), [
    ('package.module.function', {'invoke', 'function'}),
    (SourceSet(('package.alpha', 'other.beta', ('name_source', 'ignored'))),
     {'invoke', 'alpha', 'beta'}),
    (('source_set', ('package.first', 'other.second'), ''), {'invoke', 'first', 'second'}),
    (None, {'invoke'}),
])
def test_edge_names_real_analyzer_and_explicit_normalizer(tmp_path, source, expected):
    analyzer, tracers = project(tmp_path)
    edge = replace(tracers['main'].module_cg.edges[0], callee_name='object.invoke',
                   callee_source=source)
    assert analyzer._edge_callable_names(edge) == expected
    assert edge_callable_names(edge, normalize_source) == expected


def test_edge_index_rejects_same_version_other_graph(tmp_path):
    analyzer, _ = project(tmp_path)
    first, second = ProjectCallGraph(), ProjectCallGraph()
    assert first.version == second.version
    analyzer.project_cg = first
    first_index = analyzer._get_ownership_edge_index()
    analyzer.project_cg = second
    second_index = analyzer._get_ownership_edge_index()
    assert second_index is not first_index
    assert second_index.graph is second
    assert analyzer._ownership_run.edge_index is second_index


def test_edge_index_real_builder_keeps_old_index_when_name_resolution_fails(tmp_path, monkeypatch):
    analyzer, tracers = project(tmp_path)
    first = analyzer._get_ownership_edge_index()
    tracers['main'].module_cg.edges.append(replace(tracers['main'].module_cg.edges[0]))
    def fail(edge):
        raise RuntimeError('injected edge name failure')
    with monkeypatch.context() as patch:
        patch.setattr(analyzer, '_edge_callable_names', fail)
        with pytest.raises(RuntimeError, match='injected edge name failure'):
            analyzer._get_ownership_edge_index()
    assert analyzer._ownership_run.edge_index is first
    updated = analyzer._get_ownership_edge_index()
    assert updated is not first and updated.generation == analyzer.project_cg.version


def test_edge_index_build_during_graph_mutation_does_not_publish(tmp_path, monkeypatch):
    analyzer, tracers = project(tmp_path)
    old_index = analyzer._get_ownership_edge_index()
    tracers['main'].module_cg.edges.append(replace(tracers['main'].module_cg.edges[0]))
    original = analyzer._edge_callable_names
    changed = []
    def mutate_once(edge):
        names = original(edge)
        if not changed:
            tracers['main'].module_cg.edges.append(replace(edge, call_lineno=edge.call_lineno + 1000))
            changed.append(True)
        return names
    monkeypatch.setattr(analyzer, '_edge_callable_names', mutate_once)
    with pytest.raises(RuntimeError, match='call graph changed during edge indexing'):
        analyzer._get_ownership_edge_index()
    assert changed == [True]
    assert analyzer._ownership_run.edge_index is old_index
    second = analyzer._get_ownership_edge_index()
    assert second is not old_index and second.generation == analyzer.project_cg.version


def test_callable_index_is_run_local_and_invalidates_by_graph_and_rewrite(tmp_path):
    analyzer, tracers = project(tmp_path)
    run = analyzer._ownership_run
    first = analyzer._ensure_callable_lookup()
    assert run.callable_index is first
    assert analyzer._ensure_callable_lookup() is first
    analyzer._invalidate_edge_lookup(tracers['main'].module_cg.edges[0])
    assert run.callable_index is None
    second = analyzer._ensure_callable_lookup()
    assert second is not first and second.graph is analyzer.project_cg
    tracers['main'].module_cg.edges.append(replace(tracers['main'].module_cg.edges[0]))
    third = analyzer._ensure_callable_lookup()
    assert third is not second and third.generation == analyzer.project_cg.version
    replacement1, replacement2 = ProjectCallGraph(), ProjectCallGraph()
    analyzer.project_cg = replacement1
    first_empty = analyzer._ensure_callable_lookup()
    analyzer.project_cg = replacement2
    second_empty = analyzer._ensure_callable_lookup()
    assert replacement1.version == replacement2.version
    assert first_empty is not second_empty and second_empty.graph is replacement2
    assert run.callable_index is second_empty


@pytest.mark.parametrize('values', [[], ['json'], ['json.tool', '', '.x'],
                                 [SourceSet(('numpy', 'pandas.core'))]])
def test_import_index_matches_original_prefix_predicate(values):
    tracer = SingleFileAnalyzer('main')
    tracer.symbols.direct.update(dict(enumerate(values)))
    tracer.symbol_refs.append(SymbolRef('local_import', 'os.path', kind='import'))
    for symbol in ('', '.', '.x', 'jso', 'json', 'json.tool.x', 'os', 'os.path',
                   'os.paths', 'numpy', 'pandas.core', 'pandas.core.indexes', None):
        strings = [item for value in values
                   for item in (value.sources if isinstance(value, SourceSet) else (value,))
                   if isinstance(item, str)] + ['os.path']
        expected = isinstance(symbol, str) and any(
            value == symbol or value.startswith(symbol + '.')
            or symbol.startswith(value + '.') for value in strings)
        assert _is_import_origin(tracer, symbol) == expected
    assert tracer._import_origin_index is not None


def test_import_index_observes_dictionary_and_reference_rewrites():
    tracer = SingleFileAnalyzer('main')
    tracer.symbols.direct['alias'] = 'json'
    assert _is_import_origin(tracer, 'json')
    tracer.symbols.direct['alias'] = 'numpy'
    assert not _is_import_origin(tracer, 'json')
    assert _is_import_origin(tracer, 'numpy')
    tracer.symbols.restore(({'alias': 'pandas'}, {}, {}))
    assert not _is_import_origin(tracer, 'numpy')
    assert _is_import_origin(tracer, 'pandas')
    tracer.symbol_refs.append(SymbolRef('local_import', 'os.path', kind='import'))
    assert _is_import_origin(tracer, 'os')
    tracer.symbol_refs[-1] = SymbolRef('local_import', 'sys', kind='import')
    assert not _is_import_origin(tracer, 'os')
    assert _is_import_origin(tracer, 'sys')
    tracer.symbol_refs[-1].source = 'pathlib'
    assert not _is_import_origin(tracer, 'sys')
    assert _is_import_origin(tracer, 'pathlib')
    assert tracer._import_origin_index[0] is tracer.symbols.direct
    assert tracer._import_origin_index[1] is tracer.symbol_refs


def test_ast_facts_are_source_scoped_and_preserve_traversal(tmp_path):
    analyzer, tracers = project(tmp_path)
    tree = tracers['main']._module_tree
    facts = analyzer._ownership_run.ast_facts.get(tree)
    assert facts.nodes == tuple(ast.walk(tree))
    assert analyzer._ownership_run.ast_facts.get(tree) is facts
    assert facts.classes == tuple(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    path = tmp_path / 'main.py'
    path.write_text('class C: pass\n', encoding='utf-8')
    analyzer.analyze()
    replacement = analyzer._ownership_run.program.module_tracers['main']._module_tree
    assert replacement is not tree
    assert analyzer._ownership_run.ast_facts.get(replacement).classes[0].name == 'C'


def test_scope_edge_buckets_preserve_order_and_observe_changes(tmp_path):
    analyzer, tracers = project(tmp_path)
    module = tracers['main'].module_cg
    expected = tuple(edge for edge in module.edges if edge.caller.qualname == '<module>')
    assert analyzer._call_edges_in_scope('main', '<module>') == expected
    added = replace(expected[0], call_lineno=1000)
    module.edges.append(added)
    assert analyzer._call_edges_in_scope('main', '<module>') == expected + (added,)


def test_explicit_edge_rewrites_update_mapping_and_scope_buckets(tmp_path):
    analyzer, tracers = project(tmp_path)
    edge = tracers['main'].module_cg.edges[0]
    analyzer._get_edge_lookup()
    edge.mapping_targets = ()
    analyzer._invalidate_edge_lookup(edge)
    edges, _, mapped, _ = analyzer._get_edge_lookup()
    assert any(edges[index][1] is edge for index in mapped)
    edge.mapping_targets = None
    edge.caller = replace(edge.caller, qualname='changed')
    analyzer._invalidate_edge_lookup(edge)
    assert edge in analyzer._call_edges_in_scope('main', 'changed')
    assert edge not in analyzer._call_edges_in_scope('main', '<module>')
    assert not analyzer._get_edge_lookup()[2]


def test_completed_readonly_proofs_are_reused_without_caching_cycles(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text(
        'class Holder:\n def __init__(self, callback): self.callback = callback\n'
        ' def use(self): return self.callback()\n', encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    analyzer._constructor_only_fields = {'callback'}
    tracers = analyzer._ownership_run.program.module_tracers
    proofs = []
    original = analyzer._prove_constructor_field_readonly
    def record(*args, **kwargs):
        proofs.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(analyzer, '_prove_constructor_field_readonly', record)
    for _ in range(3):
        assert analyzer._constructor_field_method_is_readonly(
            ('main', 'Holder'), 'use', 'callback', tracers)
    assert len(proofs) == 1
    assert not analyzer._constructor_field_method_is_readonly(
        ('main', 'Holder'), 'use', 'callback', tracers, {(('main', 'Holder'), 'use')})
