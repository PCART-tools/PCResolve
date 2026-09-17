## @package tests.test_program_facts
#  Shared facts preserve syntax and the existing consumers' binding policies.

import ast
from dataclasses import asdict
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef, analyze_project
from pcresolve.call_graph import FunctionId, FunctionSummary, CallEdge, CallContext, ModuleCallGraph
from pcresolve.cross_file import ProjectAnalyzer
from pcresolve.ir import CallSite
from pcresolve.program_facts import (SourceSpan, FunctionSignature, bind_ast_call,
                                     bind_parameter_sources, CONTEXT_BINDING,
                                     OWNERSHIP_BINDING)


ROOT = Path(__file__).parent / 'fixtures' / 'shared_program_facts'


def _signature(text, bound=False):
    args = ast.parse(text).body[0].args
    positional = args.posonlyargs + args.args
    return FunctionSignature.from_ast(args, positional[1:] if bound else positional)


def _bind(text, signature):
    return bind_ast_call(ast.parse(text, mode='eval').body, signature)


def test_signature_preserves_parameter_kinds_and_default_nodes():
    signature = _signature('def f(a, /, b=1, *items, flag=True, required, **options): pass')
    assert signature.positional_only == ('a',)
    assert signature.positional_or_keyword == ('b',)
    assert signature.keyword_only == ('flag', 'required')
    assert signature.vararg == 'items' and signature.kwarg == 'options'
    assert {name: ast.unparse(value) for name, value in signature.defaults} == {
        'b': '1', 'flag': 'True'}


def test_bound_receiver_is_removed_without_shifting_default_identity():
    signature = _signature('def f(self, value=1, /, *, flag=True): pass', bound=True)
    assert signature.positional == ('value',)
    assert dict(signature.defaults)['value'].value == 1
    records, reasons = _bind('f(x)', signature)
    assert [(r['parameter'], r['target_path']) for r in records] == [('value', [])]
    assert reasons == []


def test_literal_expansion_binds_formals_and_variadic_paths():
    signature = _signature('def f(a, /, b, *items, flag, **options): pass')
    records, reasons = _bind("f(*(x, y, z), **{'flag': q, 'extra': r})", signature)
    assert [(r['parameter'], r['target_path'], r['binding_kind']) for r in records] == [
        ('a', [], 'starred'), ('b', [], 'starred'), ('items', [0], 'starred'),
        ('flag', [], 'expanded_keyword'), ('options', ['extra'], 'expanded_keyword')]
    assert reasons == []


def test_positional_only_keyword_is_routed_to_keyword_pack():
    signature = _signature('def f(a, /, **options): pass')
    records, reasons = _bind('f(x, a=y)', signature)
    assert [(r['parameter'], r['target_path']) for r in records] == [
        ('a', []), ('options', ['a'])]
    assert reasons == []


def test_dynamic_expansion_preserves_uncertainty_and_boundary_order():
    signature = _signature('def f(a, b, *, flag): pass')
    records, reasons = _bind('f(*xs, value, **ys, extra=q)', signature)
    assert all(r['status'] == 'unresolved' for r in records)
    assert reasons == ['dynamic_argument_expansion', 'dynamic_argument_expansion',
                       'invalid_argument_binding']


@pytest.mark.parametrize('starts, expected', [
    ({0: 'xs'}, ('xs', 1)), ({0: 'xs', 1: 'ys'}, None), ({None: 'xs'}, None)])
def test_source_binding_projects_only_unambiguous_positional_packs(starts, expected):
    signature = _signature('def f(a, b): pass')
    result = bind_parameter_sources(signature, 'b', {}, {}, starts, [],
                                    lambda source, key: (source, key), OWNERSHIP_BINDING)
    assert result == ([expected] if expected else None)


def test_consumer_policy_preserves_existing_ambiguous_keyword_default_difference():
    summary = FunctionSummary(FunctionId('main', 'f'), params=['value'],
                              positional_params=['value'], defaults={'value': 'default'})
    for policy, expected in [(CONTEXT_BINDING, None), (OWNERSHIP_BINDING, ['default'])]:
        assert bind_parameter_sources(summary.signature, 'value', {}, {}, {}, ['x', 'y'],
                                      lambda source, key: (source, key), policy) == expected


def test_consumer_policy_preserves_variadic_context_vs_owner_projection():
    signature = _signature('def f(a, *items, flag, **options): pass')
    arguments = ({0: 'a', 1: 'b'}, {'flag': 'flag', 'extra': 'extra'}, {1: 'xs'}, ['ys'])
    for parameter, expected in [('items', ['b', 'xs']), ('options', ['extra', 'ys'])]:
        assert bind_parameter_sources(signature, parameter, *arguments,
                                      lambda source, key: (source, key), OWNERSHIP_BINDING) == expected
        assert bind_parameter_sources(signature, parameter, *arguments,
                                      lambda source, key: (source, key), CONTEXT_BINDING) is None


def test_summary_signature_reflects_updated_sources_and_legacy_positional_fallback():
    summary = FunctionSummary(FunctionId('main', 'f'), params=['value', 'items', 'flag'],
                              keyword_only_params=['flag'], vararg='items',
                              defaults={'value': 'first'})
    assert summary.signature.positional == ('value', 'flag')
    summary.defaults['value'] = 'second'
    assert dict(summary.signature.defaults)['value'] == 'second'


def test_ownership_adapters_preserve_default_ambiguity_and_shape_payload_selection():
    analyzer = ProjectAnalyzer(str(ROOT))
    analyzer.analyze()
    summary = FunctionSummary(FunctionId('main', 'f'), params=['value'],
                              positional_params=['value'], defaults={'value': 'default'})
    analyzer.project_cg.modules['main'] = ModuleCallGraph('main', functions={'f': summary})
    edge = CallEdge(FunctionId('main', 'caller'), summary.id,
                    star_kwarg_sources=['x', 'y'])
    context = CallContext('main', summary.id, edge)
    assert analyzer._bounded_argument_source(context, 'value') is None
    assert analyzer._edge_parameter_sources(edge, summary, 'value', 0) == ['default']
    edge.arg_sources = {'pos': {0: 'owner'}, 'kw': {}}
    edge.protocol_arg_sources = {'pos': {0: 'shape'}}
    edge.iterable_arg_sources = {'pos': {0: 'element'}}
    assert analyzer._edge_parameter_sources(edge, summary, 'value', 0) == ['owner']
    assert analyzer._edge_parameter_sources(edge, summary, 'value', 0,
                                            prefer_protocol_shape=True) == ['shape']
    assert analyzer._edge_parameter_sources(edge, summary, 'value', 0,
                                            prefer_iterable_elements=True) == ['element']
    assert edge.arg_sources['pos'][0] == 'owner'


def test_source_projection_preserves_legacy_keyword_priority_for_positional_only():
    signature = _signature('def f(value, /): pass')
    for policy in (CONTEXT_BINDING, OWNERSHIP_BINDING):
        assert bind_parameter_sources(signature, 'value', {0: 'position'}, {'value': 'keyword'},
                                      {}, [], lambda source, key: (source, key), policy) == ['keyword']


def test_span_identity_handles_multiline_and_distinct_same_line_calls():
    calls = [n for n in ast.walk(ast.parse('f(\n x\n); f(x)')) if isinstance(n, ast.Call)]
    spans = [SourceSpan.from_ast('C:/source.py', node) for node in calls]
    assert spans[0].coordinates == (1, 0, 3, 1)
    assert spans[0].key == 'C:/source.py:1:0:3:1'
    assert spans[0] != spans[1] and spans[0].key != spans[1].key


def test_call_site_identity_is_an_internal_property_with_unchanged_serialization():
    site = CallSite('f(x)', 'f', 'x', 'f', file_path='source.py', lineno=2,
                    col_offset=4, end_lineno=2, end_col_offset=8)
    assert site.source_span.key == 'source.py:2:4:2:8'
    assert 'source_span' not in asdict(site)


def test_internal_call_and_signature_facts_agree_between_analyzers():
    ownership = ProjectAnalyzer(str(ROOT))
    ownership.analyze()
    flow = FlowAnalyzer(project_root=ROOT)
    result = flow.analyze(FunctionRef(module='main', qualname='repeated'))
    module = ownership.project_cg.modules['main']
    edges = [e for e in module.edges if e.caller.qualname == 'repeated']
    assert {e.source_span.key for e in edges} == {c.id for c in result.calls}
    assert module.functions['Decoder.parse'].signature.positional_only == ('value',)
    assert module.functions['decode'].signature.positional_only == ('value',)
    assert any(s.signature.positional_only == ('value',) for name, s in module.functions.items()
               if 'lambda' in name)
    # Properties of internal facts must not add fields to public JSON contracts.
    assert 'source_span' not in asdict(result.calls[0])
    assert all(c.top_library == 'local' for c in analyze_project(str(ROOT)).all_api_calls
               if c.func_name == 'decode')
