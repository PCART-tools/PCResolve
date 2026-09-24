## @package tests.test_value_flow_chain_receivers
#  Return-to-receiver target candidates require field-constructor provenance.

import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_enhancements'


def chain(owner):
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='chain_receivers', qualname=owner + '.run'))
    return result, next(call for call in result.calls
                        if call.callee_name.endswith('.set_ticks'))


def test_chained_receiver_uses_single_constructor_field_with_evidence():
    result, call = chain('Owner')
    assert call.target.qualname == 'Axis.set_ticks'
    assert call.target_status == 'returned_field_candidate'
    assert [item['qualname'] for item in call.target_candidates] == [
        'Axis.set_ticks']
    fact = call.receiver_type_evidence[0]
    assert fact['field'] == 'axis'
    assert fact['instance_type']['qualname'] == 'Axis'
    assert 'self.axis = Axis()' in fact['assignment']['source_text']
    assert 'return self.axis' in fact['returns'][0]['source_text']
    assert 'self.axis_for_ticks()' in fact['accessor_call']['source_text']
    assert 'self.axis_for_ticks().set_ticks' in fact['receiver_call']['source_text']
    assert any(item.get('call_id') == call.id
               and item['reason'] == 'dynamic_method_override_possible'
               for item in result.boundaries)
    serialized = result.to_dict()
    exposed = next(item for item in serialized['calls'] if item['id'] == call.id)
    assert exposed['target_candidates'][0]['qualname'] == 'Axis.set_ticks'
    assert exposed['receiver_type_evidence'][0]['field'] == 'axis'
    json.dumps(serialized)


def test_chained_receiver_with_two_known_types_has_bounded_candidates():
    result, call = chain('Bounded')
    assert call.target is None
    assert call.target_status == 'bounded_alternatives'
    assert {item['qualname'] for item in call.target_candidates} == {
        'Axis.set_ticks', 'OtherAxis.set_ticks'}
    assert len(call.receiver_type_evidence) == 2


def test_all_reachable_return_branches_share_one_field():
    result, call = chain('SameFieldBranches')
    assert call.target.qualname == 'Axis.set_ticks'
    assert call.target_status == 'returned_field_candidate'
    assert len(call.receiver_type_evidence[0]['returns']) == 2


def test_chained_receiver_stays_unresolved_without_complete_field_proof():
    for owner in ('Reassigned', 'DifferentReturns', 'UnknownParameter',
                  'DynamicAttribute', 'PartialReturn', 'EarlyInitExit',
                  'DynamicSetattr'):
        result, call = chain(owner)
        assert call.target is None, owner
        assert call.target_candidates == [], owner
        assert call.target_status == 'receiver_unresolved', owner
        assert not call.receiver_type_evidence, owner

    result, call = chain('PartialTypes')
    assert call.target is None
    assert call.target_candidates == []
    assert call.target_status == 'receiver_unresolved'


def test_chained_receiver_budget_cutoff_has_no_inferred_target():
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='chain_receivers', qualname='Owner.run'),
        max_call_contexts=1)
    call = next(item for item in result.calls
                if item.callee_name.endswith('.set_ticks'))
    assert call.target is None
    assert call.target_candidates == []
    assert call.target_status == 'receiver_unresolved'
    assert any(item['reason'] == 'budget_exceeded'
               for item in result.boundaries)


def test_matplotlib_colorbar_chain_remains_unresolved_without_axis_type():
    inventory = Path('C:/GitHub/VPPDetector/tmp/pcbench_sources/sources.json')
    if not inventory.is_file():
        pytest.skip('PCBench source inventory is not available')
    sources = json.loads(inventory.read_text(encoding='utf-8'))['sources']
    record = next((item for item in sources
                   if item['source_id'] == 'matplotlib-3.7.0'), None)
    if record is None or record['status'] != 'ready':
        pytest.skip('Matplotlib source is not available')
    package = Path(record['package_root_absolute'])
    result = FlowAnalyzer(source_files=[package / 'colorbar.py'],
                          import_roots=[package.parent]).analyze(
        FunctionRef(module='matplotlib.colorbar', qualname='Colorbar.set_ticks'))
    call = result.find_calls(callee_name='self._long_axis().set_ticks')[0]
    assert call.target is None
    assert call.target_status == 'receiver_unresolved'
    assert call.target_candidates == []
