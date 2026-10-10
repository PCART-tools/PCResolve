## @package tests.test_indexed_parameter_reads
#  Indexed incoming calls must cover variadic items and inherited fields.

import shutil
from pathlib import Path

import pytest

from pcresolve import ProjectAnalyzer
from pcresolve.sources import ContainerItem, InstanceAttribute, InstanceMethod, ParameterSource


ROOT = Path(__file__).parent / 'fixtures' / 'indexed_parameter_reads'


def _analyzer_with_noise(tmp_path):
    shutil.copyfile(ROOT / 'main.py', tmp_path / 'main.py')
    with (tmp_path / 'main.py').open('a', encoding='utf-8') as stream:
        for index in range(120):
            stream.write('unrelated_%s()\n' % index)
    analyzer = ProjectAnalyzer(str(tmp_path))
    analyzer.analyze()
    return analyzer, analyzer._ownership_run.program.module_tracers


@pytest.mark.parametrize('scope,index', [('positional', 0), ('keyword', 'decoder')])
def test_variadic_item_lookup_skips_unrelated_callers(tmp_path, monkeypatch, scope, index):
    analyzer, tracers = _analyzer_with_noise(tmp_path)
    checked = []
    original = analyzer._edge_targets_local_function

    def record(edge, *args, **kwargs):
        checked.append(edge.callee_name)
        return original(edge, *args, **kwargs)

    monkeypatch.setattr(analyzer, '_edge_targets_local_function', record)
    arguments = analyzer._parameter_pack_item_arguments(
        'main', ParameterSource(scope, 'apis'), index, tracers)
    assert arguments and all(source == 'json' for _, source in arguments)
    assert not any(name.startswith('unrelated_') for name in checked)
    assert len(checked) <= 12


def test_inherited_field_lookup_skips_unrelated_callers(tmp_path, monkeypatch):
    analyzer, tracers = _analyzer_with_noise(tmp_path)
    checked = []
    original = analyzer._edge_targets_local_function

    def record(edge, *args, **kwargs):
        checked.append(edge.callee_name)
        return original(edge, *args, **kwargs)

    monkeypatch.setattr(analyzer, '_edge_targets_local_function', record)
    owner = analyzer._resolve_instance_attribute_method_top(
        'main', InstanceAttribute('Base', 'self.payload', 'Base.read'),
        'loads', tracers)
    assert owner == 'json'
    assert not any(name.startswith('unrelated_') for name in checked)
    assert len(checked) <= 12


def test_incoming_indexes_preserve_mapping_callable_and_inherited_evidence(monkeypatch):
    analyzer = ProjectAnalyzer(str(ROOT))
    analyzer.analyze()
    tracers = analyzer._ownership_run.program.module_tracers
    queries = [('positional', 0), ('keyword', 'decoder'), ('Callable.__call__', 0)]

    def snapshot():
        arguments = [analyzer._parameter_pack_item_arguments(
            'main', ParameterSource(scope, 'apis'), index, tracers)
            for scope, index in queries]
        owner = analyzer._resolve_instance_attribute_method_top(
            'main', InstanceAttribute('Base', 'self.payload', 'Base.read'),
            'loads', tracers)
        return arguments, owner

    indexed = snapshot()
    assert all(arguments for arguments in indexed[0])
    assert indexed[1] == 'json'

    def exhaustive(module, scope):
        return tuple((caller_module, edge)
                     for caller_module, graph in analyzer.project_cg.modules.items()
                     for edge in graph.edges)

    monkeypatch.setattr(analyzer, '_target_call_edges', exhaustive)
    assert snapshot() == indexed


@pytest.mark.parametrize('source', [
    ContainerItem(ParameterSource('positional', 'apis'), 0),
    InstanceMethod(InstanceAttribute('Base', 'self.payload', 'Base.read'), 'loads'),
])
def test_unrelated_incoming_calls_do_not_truncate_owner_proof(tmp_path, monkeypatch, source):
    analyzer, tracers = _analyzer_with_noise(tmp_path)
    analyzer._ownership_proof_budget.max_queries = 64
    assert analyzer._origin_candidates('main', source, tracers) == ['json']

    def exhaustive(module, scope):
        return tuple((caller_module, edge)
                     for caller_module, graph in analyzer.project_cg.modules.items()
                     for edge in graph.edges)

    monkeypatch.setattr(analyzer, '_target_call_edges', exhaustive)
    assert analyzer._origin_candidates('main', source, tracers) == ['unknown']
