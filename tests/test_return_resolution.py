## @package tests.test_return_resolution
#  Return substitution is independent of owner and evidence collection policy.

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.return_resolution import (CallBinding, ReturnCall,
                                          ResolutionLimits,
                                          first_bound_value,
                                          resolve_return_dependencies,
                                          select_call_bindings)


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def _dependency(kind, source, relation='direct', path=None, label='evidence'):
    value = {'kind': kind, 'source': source, 'relation': relation,
             'evidence': [{'label': label}], 'conditions': [{'label': label}]}
    if path:
        value['output_path'] = list(path)
    return value


def test_call_bindings_retain_kind_order_paths_and_opaque_values():
    first = {'source': 'first'}
    bindings = (
        CallBinding('parameter', 'value', (first,), ('left',)),
        CallBinding('capture', 'value', ({'source': 'capture'},)),
        CallBinding('parameter', 'value', ({'source': 'second'},), ('right',)))
    selected = select_call_bindings(bindings, 'parameter', 'value')
    assert selected == (bindings[0], bindings[2])
    assert selected[0].values[0] is first
    assert first_bound_value(bindings, 'capture', 'value') == {'source': 'capture'}
    assert first_bound_value(bindings, 'parameter', 'missing') is None
    with pytest.raises(FrozenInstanceError):
        bindings[0].name = 'other'


def test_return_substitution_composes_paths_relations_and_call_context():
    summaries = {
        'entry': [_dependency('call_result', 'call', 'contained', ['outer'], 'entry')],
        'helper': [_dependency('parameter', 'data', 'derived', ['inner'], 'helper')],
    }
    argument = _dependency('parameter', 'input', path=['argument'], label='argument')
    calls = {'call': ReturnCall(
        'call', 'helper',
        (CallBinding('parameter', 'data', (argument,), ('slot',)),), ())}
    result = resolve_return_dependencies(
        'entry', 'input', summaries, calls)
    assert result.status == 'converged' and result.iterations == 3
    assert len(result.paths) == 1
    path = result.paths[0]
    assert path['output_path'] == ['outer', 'inner', 'slot', 'argument']
    assert path['relation'] == 'derived'
    assert [item['label'] for item in path['evidence']] == [
        'argument', 'helper', 'entry']
    assert path['call_context'] == ['call']


def test_capture_binding_is_distinct_from_same_named_parameter():
    summaries = {
        'entry': [_dependency('call_result', 'call')],
        'helper': [_dependency('capture', 'value')],
    }
    calls = {'call': ReturnCall(
        'call', 'helper',
        (CallBinding('parameter', 'value', (_dependency('parameter', 'wrong'),)),
         CallBinding('capture', 'value', (_dependency('parameter', 'right'),))), ())}
    result = resolve_return_dependencies('entry', 'right', summaries, calls)
    assert result.paths and result.paths[0]['source'] == 'right'
    assert not resolve_return_dependencies(
        'entry', 'wrong', summaries, calls).paths


def test_recursive_dependency_growth_retains_explicit_limit_status():
    summaries = {
        'entry': [_dependency('call_result', 'call')],
        'recursive': [_dependency('parameter', 'value'),
                      _dependency('call_result', 'call', path=['*'])],
    }
    calls = {'call': ReturnCall(
        'call', 'recursive',
        (CallBinding('parameter', 'value', (_dependency('parameter', 'value'),)),), ())}
    result = resolve_return_dependencies(
        'entry', 'value', summaries, calls,
        ResolutionLimits(max_iterations=3, max_dependencies=16))
    assert result.status == 'bounded' and result.iterations == 3


def test_flow_trace_uses_shared_solver_without_changing_public_shape():
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='recursive', qualname='select'), max_depth=3)
    trace = result.trace_parameter('b')
    assert trace['return_paths'] and trace['summary_status'] == 'converged'
    assert not result.trace_parameter('a')['return_paths']
    assert set(trace) == {'parameter', 'return_paths', 'status',
                          'summary_status', 'summary_iterations', 'boundaries'}
