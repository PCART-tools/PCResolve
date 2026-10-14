## @package tests.test_value_flow_capture_containers
#  Call-time captured container shapes and contents, independent of lexical names.
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = Path(__file__).parent / 'fixtures/capture_containers/library.py'


def analyze(name, depth=1):
    return FlowAnalyzer(source_files=[SOURCE], import_roots=[SOURCE.parent]).analyze(
        FunctionRef(module='library', qualname=name), max_depth=depth)


def capture(name):
    result = analyze(name)
    return next(call for call in result.calls if call.callee_name == 'inner').capture_bindings[0]


def test_capture_facts_record_current_contents_and_exact_shape():
    record = capture('direct')
    assert record['container_binding']['shape'] == 'dict'
    assert record['container_binding']['status'] == 'exact'
    assert record['container_binding']['contents_unknown'] is False
    assert record['current_sources'][0]['kind'] == 'parameter'
    assert record['current_sources'][0]['source'] == 'kwargs'
    assert record['current_sources'][0]['output_path'] == ['*']


@pytest.mark.parametrize('name', ['cleared_before', 'rebound_finite'])
def test_current_capture_contents_do_not_recover_original_parameters(name):
    record = capture(name)
    assert not any(value.get('kind') == 'parameter' and value.get('source') == 'kwargs'
                   for value in record['current_sources'])


def test_argument_effects_precede_the_call_time_capture_snapshot():
    assert capture('argument_clear')['current_sources'] == []


def test_unmodeled_sibling_nonlocal_write_cannot_publish_complete_capture_state():
    result = analyze('sibling_clear')
    assert any(b['reason'] == 'capture_binding_write_unmodeled' for b in result.boundaries)
    record = next(c for c in result.calls if c.callee_name == 'inner').capture_bindings[0]
    assert record.get('container_binding', {}).get('status') != 'exact'


def test_escaped_capture_contents_are_marked_unknown():
    assert capture('unknown_before')['container_binding']['contents_unknown'] is True


@pytest.mark.parametrize('name', ['copied', 'pop', 'cleared_inside', 'nested'])
def test_expanded_capture_container_protocols_have_exact_incoming_contexts(name):
    result = analyze(name, 3)
    calls = [call for call in result.calls if call.caller.qualname == name + '.inner']
    assert calls
    for call in calls:
        if call.callee_name.startswith('kwargs.'):
            assert call.target_status == 'local_container_protocol'
        if call.analysis_status == 'analyzed':
            assert call.analysis_contexts


def test_shape_metadata_does_not_turn_finite_capture_into_open_contents():
    result = analyze('rebound_finite', 2)
    inner = next(call for call in result.calls if call.callee_name == 'fixed')
    assert not any(value.get('kind') == 'capture' and value.get('output_path') == ['*']
                   for argument in inner.argument_sources for value in argument['sources'])


def test_alias_capture_names_share_one_object_during_expansion():
    result = analyze('shared_alias_clear', 2)
    sink = next(call for call in result.calls if call.callee_name == 'fixed')
    assert not any(value.get('kind') == 'capture' for argument in sink.argument_sources
                   for value in argument['sources'])


def test_distinct_captured_copy_does_not_clear_the_original():
    result = analyze('separate_copy_clear', 2)
    sink = next(call for call in result.calls if call.callee_name == 'fixed')
    assert any(value.get('kind') == 'capture' and value.get('source') == 'kwargs'
               for argument in sink.argument_sources for value in argument['sources'])
