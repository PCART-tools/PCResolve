## @package tests.test_call_resolution
#  Candidate lookup and call contexts preserve adapter-specific semantics.

from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.call_graph import CallContext as LegacyContext, FunctionId, ProjectCallGraph
from pcresolve.call_resolution import DefinitionRecord, DefinitionIndex, CallContext
from pcresolve.cross_file import ProjectAnalyzer
from pcresolve.program_facts import SourceSpan
from pcresolve.sources import ParameterSource


ROOT = Path(__file__).parent / 'fixtures' / 'call_resolution'


def _index():
    return DefinitionIndex((
        DefinitionRecord('main', 'entry', 'entry'),
        DefinitionRecord('main', 'entry.helper', 'nested'),
        DefinitionRecord('main', 'helper', 'module'),
        DefinitionRecord('lib', 'helper', 'imported'),
        DefinitionRecord('main', 'Duplicate', 'class', kind='class'),
        DefinitionRecord('main', 'duplicate', 'first'),
        DefinitionRecord('main', 'duplicate', 'second')))


def test_index_retains_duplicate_candidates_in_collection_order():
    index = _index()
    assert index.find('main', 'duplicate') == ('first', 'second')
    assert index.find_qualified(['main.duplicate', 'main.helper', 'main.duplicate']) == (
        'module', 'first', 'second')
    assert index.find_qualified(['main.helper'], local_module='main', local_names=['helper']) == ('module',)
    assert index.find('main', 'Duplicate', kind='class') == ('class',)
    assert index.find('main', 'Duplicate') == ()


def test_index_is_read_only_but_does_not_copy_or_freeze_source_payloads():
    payload = {'returns': 'before'}
    index = DefinitionIndex([DefinitionRecord('main', 'helper', payload)])
    payload['returns'] = 'after'
    assert index.find('main', 'helper')[0] is payload
    assert index.find('main', 'helper')[0]['returns'] == 'after'
    with pytest.raises(FrozenInstanceError):
        index.records = ()
    assert index.scopes('main') == frozenset(['helper'])


def test_qualified_collisions_preserve_module_and_scope_identity():
    index = DefinitionIndex([
        DefinitionRecord('pkg', 'inner.helper', 'nested'),
        DefinitionRecord('pkg.inner', 'helper', 'module')])
    assert index.find_qualified(['pkg.inner.helper']) == ('nested', 'module')
    assert index.find('pkg', 'inner.helper') == ('nested',)
    assert index.defining_modules('helper') == ('pkg.inner',)


def test_nearest_lexical_definition_precedes_import_alias():
    index = _index()
    imports = {'main': {'helper': 'lib.helper'}}
    assert index.resolve_name('main', 'entry', 'helper', imports) == 'nested'
    assert index.resolve_name('main', 'entry.worker', 'helper', imports) == 'nested'
    assert index.resolve_name('main', 'other', 'helper', imports) == 'imported'


def test_ambiguous_nearest_scope_does_not_fall_back_to_module():
    index = DefinitionIndex(list(_index().records) + [
        DefinitionRecord('main', 'entry.helper', 'other_nested')])
    assert index.resolve_name('main', 'entry', 'helper', {}) is None


def test_class_scope_is_not_implicit_function_scope():
    index = DefinitionIndex([
        DefinitionRecord('main', 'Box', 'class', kind='class'),
        DefinitionRecord('main', 'Box.run', 'run'),
        DefinitionRecord('main', 'Box.helper', 'method'),
        DefinitionRecord('lib', 'helper', 'imported')])
    assert index.resolve_name('main', 'Box.run', 'helper', {'main': {'helper': 'lib.helper'}}) == 'imported'


def test_alias_chain_and_cycle_are_bounded_without_reading_more_sources():
    index = _index()
    imports = {'main': {'convert': 'facade.exported'},
               'facade': {'exported': 'bridge.convert'}, 'bridge': {'convert': 'lib.helper'}}
    assert index.resolve_name('main', 'entry', 'convert', imports) == 'imported'
    assert index.resolve_name('main', 'entry', 'convert', imports, max_alias_hops=2) is None
    imports['bridge']['convert'] = 'facade.exported'
    assert index.resolve_name('main', 'entry', 'convert', imports) is None


def test_context_chain_preserves_order_and_legacy_import():
    assert LegacyContext is CallContext
    root = CallContext('main', FunctionId('main', 'entry'), None)
    child = CallContext('main', FunctionId('lib', 'helper'), None, root)
    leaf = CallContext('lib', FunctionId('lib', 'end'), None, child)
    assert tuple(leaf.chain()) == (leaf, child, root)
    assert leaf.ancestors == (root.target, child.target)
    assert root.ancestors == () and root.call_id is None
    with pytest.raises(FrozenInstanceError):
        leaf.parent = root


@pytest.fixture
def analyzers():
    owner = ProjectAnalyzer(str(ROOT))
    ownership = owner.analyze()
    flow = FlowAnalyzer(project_root=ROOT)
    flow._index()
    return owner, ownership, flow


def test_adapters_keep_existing_duplicate_collection_policy(analyzers):
    owner, _, flow = analyzers
    owner_candidates = owner._get_definition_index().find('duplicates', 'identity')
    flow_candidates = flow._definition_index.find('duplicates', 'identity')
    assert len(owner_candidates) == 1 and len(flow_candidates) == 2
    caller = FunctionRef(module='duplicates', qualname='entry')
    assert flow._resolve(caller, 'identity') is None


@pytest.mark.parametrize('name', ['entry', 'nested.identity', 'Decoder.parse'])
def test_definition_locations_agree_between_adapters(analyzers, name):
    owner, _, flow = analyzers
    summary = owner._get_definition_index().find('main', name)[0]
    ref, node = flow._definition_index.find('main', name)[0]
    assert summary.definition_span == SourceSpan.from_ast(ref.file_path, node)
    assert '_definition_index' not in flow.analyze(FunctionRef(module='main', qualname='entry')).to_dict()


def test_same_line_calls_have_shared_context_identity(analyzers):
    owner, _, flow = analyzers
    result = flow.analyze(FunctionRef(module='main', qualname='repeated'))
    edges = [e for e in owner.project_cg.modules['main'].edges if e.caller.qualname == 'repeated']
    ids = {CallContext('main', e.callee, e).call_id for e in edges}
    assert len(ids) == 2 and ids == {CallContext('main', c.target, c).call_id for c in result.calls}
    assert all('definition_span' not in asdict(c) for c in result.calls)


def test_nested_reexport_and_method_targets_remain_distinct(analyzers):
    _, ownership, flow = analyzers
    cases = [('entry', 'helpers', 'identity'), ('nested', 'main', 'nested.identity'),
             ('Decoder.parse', 'main', 'Decoder.identity')]
    for entry, module, qualname in cases:
        result = flow.analyze(FunctionRef(module='main', qualname=entry), max_depth=2)
        assert (result.calls[0].target.module, result.calls[0].target.qualname) == (module, qualname)
        assert result.trace_parameter('value')['return_paths']
    assert {c.top_library for c in ownership.all_api_calls if c.func_name == 'identity'} == {'local'}


def test_recursive_walk_and_selected_expansion_keep_recursion_boundary(analyzers):
    _, _, flow = analyzers
    entry = FunctionRef(module='main', qualname='recursive')
    result = flow.analyze(entry)
    expanded = flow.expand(result, result.calls[0].id, additional_depth=3)
    direct = flow.analyze(entry, max_depth=4)
    assert expanded.calls == direct.calls and expanded.boundaries == direct.boundaries
    assert [b['reason'] for b in expanded.boundaries] == ['recursion']
    assert result.boundaries[0]['reason'] == 'depth_limit'


def test_ownership_pack_selection_walks_the_shared_parent_chain(analyzers):
    owner, _, _ = analyzers
    graph = owner.project_cg.modules['main']
    edge = next(e for e in graph.edges if e.caller.qualname == 'consume' and e.callee_name == 'forwarding')
    outer = CallContext('main', graph.functions['forwarding'].id, edge)
    child_edge = next(e for e in graph.edges if e.caller.qualname == 'forwarding')
    child = CallContext('main', graph.functions['unpack'].id, child_edge, outer)
    source = ParameterSource('forwarding', 'options')
    selected = owner._bounded_pack_item_source(child, source, 'value')
    assert selected == ('main', edge.arg_sources['kw']['value'], None)


def test_owner_index_rebuilds_for_a_new_analysis_graph(analyzers):
    owner, _, _ = analyzers
    previous = owner._get_definition_index()
    owner.project_cg = ProjectCallGraph()
    assert not owner._get_definition_index().records
    assert previous.find('main', 'entry')


def test_flow_refreshes_definition_index_after_source_edit(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text('def helper(value): return value\ndef entry(value): return helper(value)\n', encoding='utf-8')
    flow = FlowAnalyzer(project_root=tmp_path)
    result = flow.analyze(FunctionRef(module='main', qualname='entry'))
    old_index = flow._definition_index
    path.write_text('def other(value): return value\ndef entry(value): return other(value)\n', encoding='utf-8')
    current = flow.analyze(result.entry)
    assert old_index.find('main', 'helper') and not flow._definition_index.find('main', 'helper')
    assert current.calls[0].target.qualname == 'other'
