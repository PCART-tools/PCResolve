## @package tests.test_indexed_dispatch
#  Indexed candidate lookup must preserve exhaustive dispatch semantics.

import shutil
from dataclasses import replace
from pathlib import Path

from pcresolve import ProjectAnalyzer
from pcresolve.sources import SourceSet


ROOT = Path(__file__).parent / 'fixtures' / 'indexed_dispatch'


def test_unrelated_definitions_do_not_expand_target_matching(tmp_path, monkeypatch):
    for source in ROOT.glob('*.py'):
        shutil.copyfile(source, tmp_path / source.name)
    with (tmp_path / 'main.py').open('a', encoding='utf-8') as stream:
        for index in range(120):
            stream.write('\ndef unused_%s(value):\n    return value\n' % index)
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    edge = next(edge for edge in analyzer.project_cg.modules['main'].edges
                if edge.callee_name == 'alias')
    edge = replace(edge, callee_source='decode')
    queries = []
    original = analyzer._edge_targets_local_function

    def record(*args, **kwargs):
        queries.append((args[2], args[3]))
        return original(*args, **kwargs)

    monkeypatch.setattr(analyzer, '_edge_targets_local_function', record)
    targets = analyzer._local_edge_targets(edge, 'main', tracers)
    assert targets
    assert not any(name.startswith('unused_') for _, name in queries)
    assert len(queries) <= 12


def test_dispatch_candidates_match_exhaustive_lookup():
    analyzer = ProjectAnalyzer(str(ROOT))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    candidates = analyzer._get_definition_index().records_for()
    for module, graph in analyzer.project_cg.modules.items():
        edges = list(graph.edges)
        if module == 'main':
            template = next(edge for edge in edges if edge.callee_name == 'alias')
            edges.extend([
                replace(template, callee_source='decode'),
                replace(template, callee_source='nested.inner'),
                replace(template, callee_source=SourceSet(('decode', 'alternate'))),
            ])
        for edge in edges:
            expected = [candidate.payload.id for candidate in candidates
                        if analyzer._edge_targets_local_function(
                            edge, module, candidate.module, candidate.qualname,
                            tracers[module], tracers)]
            if not expected:
                expected = [candidate.payload.id for candidate in candidates
                            if analyzer._edge_targets_local_function(
                                edge, module, candidate.module, candidate.qualname,
                                tracers[module], tracers, allow_inherited_dispatch=True)]
                expected = analyzer._nearest_inherited_method_targets(expected, tracers)
            assert analyzer._local_edge_targets(edge, module, tracers) == list(
                dict.fromkeys(expected)), edge.callee_name


def test_parameter_lookup_does_not_check_unrelated_call_edges(tmp_path, monkeypatch):
    for source in ROOT.glob('*.py'):
        shutil.copyfile(source, tmp_path / source.name)
    with (tmp_path / 'main.py').open('a', encoding='utf-8') as stream:
        stream.write("\n" + "unrelated('x')\n" * 120)
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    checked = []
    original = analyzer._edge_targets_local_function

    def record(*args, **kwargs):
        checked.append(args[0].callee_name)
        return original(*args, **kwargs)

    monkeypatch.setattr(analyzer, '_edge_targets_local_function', record)
    found = []
    analyzer._collect_project_edge_arguments(
        'main', 'decode', 'value', 0, tracers, found, set(), False, False, None)
    assert found
    assert 'unrelated' not in checked
    assert len(checked) <= 12


def test_reverse_index_retains_every_exhaustive_target_and_mapping():
    analyzer = ProjectAnalyzer(str(ROOT))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    graph = analyzer.project_cg.modules['main']
    template = next(edge for edge in graph.edges if edge.callee_name == 'alias')
    graph.edges.extend([
        replace(template, callee_source='nested.inner'),
        replace(template, callee_source=SourceSet(('decode', 'alternate'))),
        replace(template, mapping_targets=(graph.functions['decode'].id,),
                mapping_targets_complete=True),
    ])
    for candidate in analyzer._get_definition_index().records_for():
        expected = [(module, id(edge))
                    for module, cg in analyzer.project_cg.modules.items()
                    for edge in cg.edges
                    if analyzer._edge_targets_local_function(
                        edge, module, candidate.module, candidate.qualname,
                        tracers[module], tracers, allow_inherited_dispatch=True)]
        selected = analyzer._target_call_edges(candidate.module, candidate.qualname)
        actual = [(module, id(edge)) for module, edge in selected
                  if analyzer._edge_targets_local_function(
                      edge, module, candidate.module, candidate.qualname,
                      tracers[module], tracers, allow_inherited_dispatch=True)]
        assert actual == expected, candidate.qualname


def test_reverse_index_observes_rewritten_callable_sources(monkeypatch):
    analyzer = ProjectAnalyzer(str(ROOT))
    analyzer.analyze()
    graph = analyzer.project_cg.modules['main']
    template = next(edge for edge in graph.edges if edge.callee_name == 'alias')
    edge = replace(template, callee_name='items[0]', callee_source='local',
                   call_lineno=1000)
    graph.edges.append(edge)
    assert not any(candidate is edge for _, candidate in analyzer._target_call_edges(
        'main', 'decode'))
    inspected = []
    original = analyzer._edge_callable_names

    def record(candidate):
        inspected.append(candidate)
        return original(candidate)

    monkeypatch.setattr(analyzer, '_edge_callable_names', record)
    analyzer._rewrite_mapped_result_edges(graph, template, 'items', 'decode', None)
    assert any(candidate is edge for _, candidate in analyzer._target_call_edges(
        'main', 'decode'))
    assert len(inspected) <= 2


def test_unrelated_callers_do_not_exhaust_a_valid_owner_proof(tmp_path, monkeypatch):
    (tmp_path / 'main.py').write_text(
        "import json\ndef forward(api):\n    return api.loads('{}')\nforward(json)\n"
        + ''.join('unrelated_%s()\n' % index for index in range(40)),
        encoding='utf-8')
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    source = next(call['base'] for call in tracers['main'].api_calls
                  if call['func_name'] == 'api.loads')
    analyzer._ownership_proof_budget.max_queries = 16
    assert analyzer._origin_candidates('main', source, tracers) == ['json']

    def exhaustive(module, scope):
        return tuple((caller_module, edge)
                     for caller_module, graph in analyzer.project_cg.modules.items()
                     for edge in graph.edges)

    monkeypatch.setattr(analyzer, '_target_call_edges', exhaustive)
    assert analyzer._origin_candidates('main', source, tracers) == ['unknown']
