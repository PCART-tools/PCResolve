## @package tests.test_indexed_callable_dispatch
#  Callable instance indexes retain aliases, inherited and dynamic evidence.

from pathlib import Path
from dataclasses import replace

from pcresolve import ProjectAnalyzer
from pcresolve.sources import CallResult


ROOT = Path(__file__).parent / 'fixtures' / 'indexed_callable_dispatch'


def test_callable_parameter_lookup_skips_unrelated_edges(tmp_path, monkeypatch):
    source = (ROOT / 'main.py').read_text(encoding='utf-8')
    (tmp_path / 'main.py').write_text(source + ''.join(
        'unrelated_%s()\n' % index for index in range(150)), encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    checked = []
    original = analyzer._edge_targets_local_function

    def record(edge, *args, **kwargs):
        checked.append(edge.callee_name)
        return original(edge, *args, **kwargs)

    monkeypatch.setattr(analyzer, '_edge_targets_local_function', record)
    found = []
    analyzer._collect_project_edge_arguments(
        'main', 'Decode.__call__', 'api', 0, tracers, found, set(), False, False, None)
    assert found
    assert not any(name.startswith('unrelated_') for name in checked)


def test_callable_reverse_index_matches_exhaustive_targets():
    analyzer = ProjectAnalyzer(str(ROOT))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    for scope in ('Decode.__call__', 'Alternate.__call__'):
        expected = [(module, id(edge))
                    for module, graph in analyzer.project_cg.modules.items()
                    for edge in graph.edges
                    if analyzer._edge_targets_local_function(
                        edge, module, 'main', scope, tracers[module], tracers,
                        allow_inherited_dispatch=True)]
        actual = [(module, id(edge))
                  for module, edge in analyzer._target_call_edges('main', scope)
                  if analyzer._edge_targets_local_function(
                      edge, module, 'main', scope, tracers[module], tracers,
                      allow_inherited_dispatch=True)]
        assert actual == expected
        assert actual


def test_callable_index_is_refreshed_on_reanalysis(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text((ROOT / 'main.py').read_text(encoding='utf-8'), encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    path.write_text('class Decode:\n def __call__(self, api): pass\n'
                    'callback = Decode()\ncallback(None)\n', encoding='utf-8')
    analyzer.analyze()
    calls = analyzer._target_call_edges('main', 'Decode.__call__')
    assert any(edge.callee_name == 'callback' for _, edge in calls)
    assert all(edge.callee_name != 'alias' for _, edge in calls)


def test_callable_reverse_index_observes_rewritten_receiver():
    analyzer = ProjectAnalyzer(str(ROOT))
    analyzer.analyze()
    graph = analyzer.project_cg.modules['main']
    template = next(edge for edge in graph.edges if edge.callee_name == 'other')
    edge = replace(template, call_lineno=1000, callee=CallResult('Alternate'))
    graph.edges.append(edge)
    assert not any(candidate is edge for _, candidate in analyzer._target_call_edges(
        'main', 'Decode.__call__'))
    edge.callee = CallResult('Decode')
    analyzer._invalidate_edge_lookup(edge)
    assert any(candidate is edge for _, candidate in analyzer._target_call_edges(
        'main', 'Decode.__call__'))
