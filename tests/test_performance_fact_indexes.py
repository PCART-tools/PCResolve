## @package tests.test_performance_fact_indexes
#  Indexed lookups retain conservative answers across mutable fact generations.

import ast
from dataclasses import replace

import pytest

from pcresolve import ProjectAnalyzer
from pcresolve.cross_file import _is_import_origin
from pcresolve.ir import SymbolRef
from pcresolve.single_file import SingleFileAnalyzer
from pcresolve.sources import CallResult, SourceSet


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
