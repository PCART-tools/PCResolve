## @package tests.test_value_flow_local_reexports
#  Local-import reexports preserve lexical bindings and variadic sources.

from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_local_reexports'


def analyze(entry):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='consumer', qualname='Owner.' + entry), max_depth=2)


def assert_variadic_sources(call):
    for parameter in ('args', 'kwargs'):
        assert any(source['kind'] == 'parameter'
                   and source['source'] == parameter
                   and source.get('output_path') == ['*']
                   for argument in call.argument_sources
                   for source in argument['sources']), parameter


@pytest.mark.parametrize('entry, callee', [
    ('together', 'together'),
    ('aliased', 'simplify'),
    ('reexport_alias', 'simplify'),
    ('module_alias', 'algorithms.together'),
    ('module_alias_before_write', 'algorithms.together'),
    ('later_rebind', 'together'),
])
def test_local_import_follows_reexports_without_same_named_method_fallback(entry, callee):
    result = analyze(entry)
    call = result.find_calls(callee_name=callee)[0]
    assert call.target is not None
    assert call.target.module == 'exports.leaf'
    assert call.target.qualname == 'together'
    assert len(call.target_candidates) == 1
    assert_variadic_sources(call)


def test_local_import_of_class_preserves_existing_member_target():
    result = analyze('imported_class_member')
    call = result.find_calls(callee_name='Klass.aliased')[0]
    assert call.target is not None
    assert (call.target.module, call.target.qualname) == ('consumer', 'Owner.aliased')
    assert_variadic_sources(call)


@pytest.mark.parametrize('entry', [
    'rebound',
    'conditional_missing',
    'conditional_targets',
    'for_missing_binding',
    'while_missing_binding',
    'cyclic',
    'reassigned_export',
    'ambiguous_export',
    'conditional_export',
])
def test_unproven_local_import_bindings_preserve_uncertainty(entry):
    result = analyze(entry)
    call = result.find_calls(callee_name='together')[0]
    assert call.target is None
    assert len(call.target_candidates) != 1
    assert any(boundary.get('call_id') == call.id
               for boundary in result.boundaries)
    assert_variadic_sources(call)


def test_local_module_attribute_reassignment_invalidates_import_target():
    result = analyze('module_attribute_rebound')
    call = result.find_calls(callee_name='algorithms.together')[0]
    assert call.target is None
    assert len(call.target_candidates) != 1
    assert any(boundary.get('call_id') == call.id
               for boundary in result.boundaries)
    assert_variadic_sources(call)
