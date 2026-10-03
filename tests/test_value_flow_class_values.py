## @package tests.test_value_flow_class_values
#  Factory-returned class facts enable only source-backed safe allocation.

import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_class_values'


def analyze(entry):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='cases', qualname=entry), max_depth=4)


def call_named(result, callee, entry):
    return next(call for call in result.find_calls(callee_name=callee)
                if call.caller.qualname == entry)


def kwargs_sources(call):
    return [source for argument in call.argument_sources
            for source in argument['sources']
            if source['kind'] == 'parameter' and source['source'] == 'kwargs']


@pytest.mark.parametrize('entry, factory, module, class_name', [
    ('same_module', 'select_same', 'cases', 'Client'),
    ('module_alias', 'select_module_alias', 'cases', 'Client'),
    ('local_alias', 'select_local_alias', 'cases', 'Client'),
    ('imported', 'select_imported', 'provider', 'External'),
    ('module_attribute', 'select_module_attribute', 'provider', 'External'),
    ('local_import', 'select_local_import', 'provider', 'External'),
    ('nested', 'select_nested', 'cases', 'select_nested.Nested'),
])
def test_factory_returned_class_identity_drives_constructor_and_method_targets(
        entry, factory, module, class_name):
    result = analyze(entry)
    selected = call_named(result, factory, entry)
    assert any(source['kind'] == 'class' and source['module'] == module
               and source['source'] == class_name and source.get('evidence')
               for source in selected.result_sources)
    constructed = call_named(result, 'impl', entry)
    assert constructed.target is not None
    assert constructed.target.module == module
    assert constructed.target.qualname == class_name + '.__init__'
    assert any(source.get('instance_type', {}).get('module') == module
               and source['instance_type']['qualname'] == class_name
               and source.get('evidence')
               for source in constructed.result_sources)
    initialized = call_named(result, 'instance.initialize', entry)
    assert initialized.target is not None
    assert initialized.target.module == module
    assert initialized.target.qualname == class_name + '.initialize'
    assert any(source.get('output_path') == ['*']
               for source in kwargs_sources(initialized))
    json.dumps(result.to_dict())


@pytest.mark.parametrize('entry, allocator, class_name', [
    ('allocated_object', 'object.__new__', 'Client'),
    ('Allocator.create', 'super(Allocator, impl).__new__', 'Backend'),
])
def test_explicit_builtin_allocation_proves_instance_only_with_known_mro(
        entry, allocator, class_name):
    result = analyze(entry)
    allocated = call_named(result, allocator, entry)
    assert any(source.get('instance_type', {}).get('qualname') == class_name
               and source.get('evidence') for source in allocated.result_sources)
    initialized = call_named(result, 'instance.initialize', entry)
    assert initialized.target is not None
    assert initialized.target.qualname == class_name + '.initialize'
    assert any(source.get('output_path') == ['*']
               for source in kwargs_sources(initialized))


@pytest.mark.parametrize('entry, allocator', [
    ('Allocator.shadowed_current_class', 'super(Allocator, impl).__new__'),
    ('Allocator.rebound_current_class', 'super(Allocator, impl).__new__'),
    ('Allocator.extra_argument', 'super(Allocator, impl).__new__'),
    ('Allocator.keyword_argument', 'super(Allocator, impl).__new__'),
    ('allocated_object_extra', 'object.__new__'),
    ('allocated_object_keyword', 'object.__new__'),
])
def test_builtin_allocator_requires_unshadowed_current_class_and_exact_signature(
        entry, allocator):
    result = analyze(entry)
    allocated = call_named(result, allocator, entry)
    assert allocated.target_status != 'builtin_allocation'
    assert not any(source.get('instance_type')
                   for source in allocated.result_sources)
    initialized = call_named(result, 'instance.initialize', entry)
    assert initialized.target is None
    assert len(initialized.target_candidates) != 1
    assert any(boundary.get('call_id') == initialized.id
               for boundary in result.boundaries)
    assert any(source.get('output_path') == ['*']
               for source in kwargs_sources(initialized))


@pytest.mark.parametrize('entry', [
    'unknown_backend_result',
    'unknown_parameter',
    'known_parameter_forwarding',
    'optional_class',
    'fallthrough_class',
    'multiple_candidates',
    'rebound_class',
    'rebound_imported_alias',
    'rebound_module_alias',
    'changed_module_namespace',
    'rebound_impl',
    'receiver_class_modified',
    'derived_class_receiver',
    'derived_instance_receiver',
    'projected_instance_receiver',
    'deleted_class_value',
    'deleted_instance_value',
    'rebound_object',
    'custom_metaclass',
    'custom_class_descriptor',
    'custom_static_descriptor',
    'custom_new',
    'unknown_mro',
    'allocated_unknown_object',
    'UnknownAllocator.create',
    'Allocator.shadowed_super',
])
def test_unproven_class_or_allocation_does_not_create_single_receiver_target(entry):
    result = analyze(entry)
    initialized = call_named(result, 'instance.initialize', entry)
    assert initialized.target is None
    assert len(initialized.target_candidates) != 1
    assert any(boundary.get('call_id') == initialized.id
               for boundary in result.boundaries)
    assert any(source.get('output_path') == ['*']
               for source in kwargs_sources(initialized))


def test_instance_receiver_alias_preserves_source_class_and_kwargs_flow():
    result = analyze('instance_alias')
    initialized = call_named(result, 'initialized.initialize', 'instance_alias')
    assert initialized.target is not None
    assert initialized.target.qualname == 'Client.initialize'
    assert any(source.get('output_path') == ['*']
               for source in kwargs_sources(initialized))


def test_instance_method_accessed_through_class_keeps_explicit_self_binding():
    result = analyze('class_unbound_method')
    call = call_named(result, 'implementation.initialize', 'class_unbound_method')
    assert call.target is not None
    assert call.target.qualname == 'Client.initialize'
    binding = next(item for item in call.parameter_bindings
                   if item['argument'] == {'position': 0})
    assert binding['parameter'] == 'self'
    assert binding['status'] == 'exact'
    assert call.binding_status != 'invalid'
    assert not any(item['argument'] == {'receiver': True}
                   for item in call.argument_sources)
    assert any(source['kind'] == 'parameter' and source['source'] == 'receiver'
               for item in call.argument_sources if item['parameter'] == 'self'
               for source in item['sources'])
    assert any(source.get('output_path') == ['*']
               for source in kwargs_sources(call))


def test_class_return_target_resolution_preserves_mapping_update_sources():
    result = analyze('mapping_update')
    initialized = call_named(result, 'instance.initialize', 'mapping_update')
    assert initialized.target is not None
    assert initialized.target.qualname == 'Client.initialize'
    assert any(source.get('output_path') == ['*']
               for source in kwargs_sources(initialized))
    assert any(source['kind'] == 'parameter' and source['source'] == 'value'
               and source.get('output_path') == ['added']
               for argument in initialized.argument_sources
               for source in argument['sources'])
    assert any(effect['operation'] == 'update'
               for effect in result.functions[0]['mapping_effects'])


def test_class_return_target_resolution_preserves_mapping_clear():
    result = analyze('mapping_clear')
    initialized = call_named(result, 'instance.initialize', 'mapping_clear')
    assert initialized.target is not None
    assert initialized.target.qualname == 'Client.initialize'
    assert not kwargs_sources(initialized)
    assert call_named(result, 'kwargs.clear', 'mapping_clear').target_status == (
        'local_container_protocol')


def test_class_return_target_resolution_preserves_finite_mapping_branch_sources():
    result = analyze('finite_mapping')
    initialized = call_named(result, 'instance.initialize', 'finite_mapping')
    assert initialized.target is not None
    assert initialized.target.qualname == 'Client.initialize'
    sources = kwargs_sources(initialized)
    assert {tuple(source.get('projection', [])) for source in sources} == {
        ('first',), ('second',)}
    assert all(source.get('conditions') for source in sources)


def test_shared_allocator_preserves_unknown_context_in_merged_status_and_results():
    result = analyze('mixed_allocator_contexts')
    allocated = call_named(result, 'object.__new__', 'ContextAllocator.allocate')
    assert allocated.target_status == 'receiver_unresolved'
    assert allocated.target is None
    typed_sources = [source for source in allocated.result_sources
                     if source.get('instance_type')]
    assert typed_sources
    assert all(source.get('value_incomplete') for source in typed_sources)
    initialized = call_named(result, 'instance.initialize', 'ContextAllocator.allocate')
    assert initialized.target_status == 'receiver_unresolved'
    assert initialized.target is None
    assert any(boundary.get('call_id') == initialized.id
               and boundary['reason'] == 'receiver_unresolved'
               for boundary in result.boundaries)
    assert any(source.get('output_path') == ['*']
               for source in kwargs_sources(initialized))
