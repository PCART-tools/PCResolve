## @package tests.test_value_flow_callable_guards
#  Conditional callable identities retain parameter roots and branch evidence.
from dataclasses import asdict
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures/value_flow_callable_guards'


def analyze(entry, **options):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), **options)


def invocation(result, name='metric'):
    return result.find_calls(callee_name=name)[0]


@pytest.mark.parametrize('entry', [
    'positive', 'reversed_guard', 'negative_else', 'negative_early_return',
    'negated_guard', 'conjunction', 'short_circuit', 'short_circuit_or',
    'conditional_expression', 'conditional_negative',
])
def test_equality_branch_binds_source_function_without_replacing_parameter_root(entry):
    call = invocation(analyze(entry))
    assert call.target is not None and call.target.qualname == 'fixed'
    value = call.callable_sources[0]
    assert value['kind'] == 'parameter' and value['source'] == 'metric'
    assert value['callable_type']['qualname'] == 'fixed'
    assert value['callable_evidence'] and value['conditions']


@pytest.mark.parametrize('entry', ['imported_guard', 'module_guard'])
def test_stable_source_import_can_supply_guard_identity(entry):
    call = invocation(analyze(entry))
    assert call.target is not None
    assert (call.target.module, call.target.qualname) == ('helpers', 'imported_fixed')


@pytest.mark.parametrize('entry', [
    'equality', 'unequal_branch', 'false_branch', 'unguarded_after_join',
    'shadowed_target', 'shadowed_module', 'escaped', 'modified', 'chained',
    'callable_only', 'decorated_guard',
])
def test_nonidentity_unknown_or_invalidated_proofs_never_select_a_fixed_target(entry):
    assert invocation(analyze(entry)).target is None


@pytest.mark.parametrize('entry', [
    'rebound', 'local_target_rebound', 'finite_alternatives',
])
def test_local_binding_overrides_the_module_spelling(entry):
    call = invocation(analyze(entry))
    assert call.target is not None and call.target.qualname == 'accepts'


def test_alias_created_after_guard_keeps_parameter_root_and_guard_evidence():
    call = invocation(analyze('alias_after_guard'), 'chosen')
    assert call.target is not None and call.target.qualname == 'fixed'
    assert call.callable_sources[0]['source'] == 'metric'
    assert call.callable_sources[0]['callable_evidence']


@pytest.mark.parametrize('entry', [
    'contradictory', 'known_other', 'known_string', 'contradictory_alternatives',
])
def test_closed_incoming_identity_excludes_an_incompatible_equality_branch(entry):
    result = analyze(entry, max_depth=3)
    assert not any(call.target and call.target.qualname == 'fixed'
                   for call in result.find_calls(callee_name='metric'))


def test_distinct_queries_and_incoming_contexts_keep_the_guard_local():
    engine = FlowAnalyzer(project_root=ROOT)
    identity = FunctionRef(module='cases', qualname='positive')
    first = engine.analyze(identity)
    saved = asdict(first)
    engine.analyze(FunctionRef(module='cases', qualname='contexts'), max_depth=3)
    assert asdict(first) == saved == asdict(engine.analyze(identity))


def test_source_guard_expands_through_existing_call_edge():
    engine = FlowAnalyzer(project_root=ROOT)
    result = engine.analyze(FunctionRef(module='cases', qualname='positive'))
    call = invocation(result)
    assert call.target is not None
    expanded = engine.expand(result, call.id)
    assert any(item['function']['qualname'] == 'fixed' for item in expanded.functions)
    assert not any(item['function']['qualname'] == 'fixed' for item in result.functions)


def test_explicit_callback_with_dynamic_keywords_retains_normal_binding_condition():
    result = analyze('known_same', max_depth=3)
    call = next(c for c in result.find_calls(callee_name='metric') if c.target is not None)
    conditions = call.callable_sources[0]['conditions']
    assert any(c.get('normal_call_binding', {}).get('parameter') == 'metric' for c in conditions)
    assert any(c.get('test', {}).get('source_text') == 'metric is fixed' for c in conditions)


def test_dynamic_positional_pack_does_not_guess_an_ordinary_callback_binding():
    result = analyze('unknown_expansion')
    edge = result.find_calls(callee_name='positive')[0]
    engine = FlowAnalyzer(project_root=ROOT)
    engine.analyze(FunctionRef(module='cases', qualname='positive'))
    target = next(d for d in engine.definitions if d[0].qualname == 'positive')
    assert not engine._incoming_facts(target, edge)


def test_invalid_duplicate_binding_does_not_supply_incoming_facts():
    result = analyze('invalid_duplicate')
    edge = result.find_calls(callee_name='positive')[0]
    assert edge.binding_status == 'invalid'


def test_compound_guard_does_not_restore_identity_after_a_named_expression_write():
    call = invocation(analyze('rebound_in_condition'))
    assert call.target is None or call.target.qualname == 'accepts'
