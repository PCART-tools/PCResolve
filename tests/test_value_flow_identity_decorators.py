## @package tests.test_value_flow_identity_decorators

import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_identity_decorators'


def analyze(entry):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='consumer', qualname=entry), max_depth=2)


@pytest.mark.parametrize('entry,decorator', [
    ('advertised', 'advertise'), ('pure', 'pure_identity')])
def test_identity_decorator_preserves_exact_source_target_and_evidence(entry, decorator):
    result = analyze(entry)
    call = result.find_calls(callee_name='targets.' + entry)[0]
    assert call.target is not None
    assert (call.target.module, call.target.qualname) == ('targets', entry)
    assert call.target_status == 'resolved'
    assert [(item['module'], item['qualname']) for item in call.target_candidates] == [
        ('targets', entry)]
    assert len(call.decorator_identity_evidence) == 1
    fact = call.decorator_identity_evidence[0]
    assert fact['decorator']['module'] == 'decorators'
    assert fact['decorator']['qualname'] == decorator
    assert fact['parameter'] == 'original'
    assert fact['returns']
    assert all(span['source_text'] == 'return original' for span in fact['returns'])
    assert result.trace_parameter('value')['return_paths']
    assert any(flow['source_parameter'] == 'value'
               and flow['target_parameter'] == 'value'
               for flow in call.parameter_flows)
    json.dumps(result.to_dict())


def test_metadata_identity_retains_effect_boundary():
    result = analyze('advertised')
    call = result.find_calls(callee_name='targets.advertised')[0]
    assert call.target is not None
    assert any(boundary.get('call_id') == call.id
               and boundary['reason'] == 'identity_decorator_effects_unmodeled'
               for boundary in result.boundaries)


def test_replacement_decorator_resolves_replacement_without_stripping_it():
    result = analyze('replaced')
    call = result.find_calls(callee_name='targets.replaced')[0]
    assert call.target is not None
    assert (call.target.module, call.target.qualname) == (
        'decorators', 'replace.replacement')
    assert call.target_status == 'decorator_replacement'
    assert not result.trace_parameter('value')['return_paths']


@pytest.mark.parametrize('entry,name', [
    ('wrapped', 'targets.wrapped'),
    ('unknown', 'targets.unknown'),
    ('rebound_formal', 'targets.rebound_formal'),
    ('deleted_formal', 'targets.deleted_formal'),
    ('conditional', 'targets.conditional'),
    ('incomplete', 'targets.incomplete'),
    ('asynchronous', 'targets.asynchronous'),
    ('generator', 'targets.generator'),
    ('code_changed', 'targets.code_changed'),
    ('alias_code_changed', 'targets.alias_code_changed'),
    ('asynchronously_replaced', 'targets.asynchronously_replaced'),
    ('module_attribute_changed', 'mutated'),
    ('rebound_symbol', 'rebound'),
    ('class_shadow', 'targets.Holder.shadowed')])
def test_unproven_decorators_do_not_expose_original_target(entry, name):
    result = analyze(entry)
    call = result.find_calls(callee_name=name)[0]
    assert call.target is None
    assert call.target_candidates == []
    assert call.binding_status == 'unavailable'
    assert any(boundary.get('call_id') == call.id for boundary in result.boundaries)
