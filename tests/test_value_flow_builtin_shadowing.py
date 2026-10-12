from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_builtin_shadowing'


def analyze(module, entry, analyzer=None):
    return (analyzer or FlowAnalyzer(project_root=ROOT)).analyze(
        FunctionRef(module=module, qualname=entry), max_depth=3)


def assert_no_builtin_facts(result, name, parameter):
    call = result.find_calls(callee_name=name)[0]
    assert call.target_status not in ('local_container_protocol', 'python_protocol', 'builtin_boundary')
    assert not any(item.get('container_object', {}).get('identity') in ('shallow_copy', 'argument_alias')
                   for item in call.result_sources)
    assert not any(item.get('operation') == 'copy' for item in call.effects)
    assert not any('Python builtin result dependency' in evidence.get('provenance', '')
                   for value in call.return_dependencies for evidence in value.get('evidence', []))
    assert not result.trace_parameter(parameter)['return_paths']


def test_conditional_dict_replacement_has_no_kwargs_return_dependency():
    result = analyze('shadow_repro', 'run')
    assert not result.trace_parameter('kwargs')['return_paths'], (
        'dict is conditionally bound to replacement(), which always returns {value: 0}; '
        'kwargs must not become a copied return dependency')
    assert_no_builtin_facts(result, 'dict', 'kwargs')


def test_conditional_tuple_replacement_has_no_args_return_dependency():
    assert_no_builtin_facts(analyze('shadow_sequence', 'run'), 'tuple', 'args')


@pytest.mark.parametrize('module', [
    'module_if', 'module_try', 'module_import', 'module_definitions', 'global_writes', 'wildcard'])
@pytest.mark.parametrize('entry,name,parameter', [
    ('mapping_call', 'dict', 'kwargs'), ('list_call', 'list', 'args'), ('tuple_call', 'tuple', 'args')])
def test_module_and_global_shadowing_blocks_both_builtin_consumers(module, entry, name, parameter):
    result = analyze(module, entry)
    assert_no_builtin_facts(result, name, parameter)
    assert result.boundaries


@pytest.mark.parametrize('module', ['module_if', 'module_try', 'module_import'])
@pytest.mark.parametrize('name', ['list', 'tuple'])
def test_shadowed_sequence_return_summary_cannot_bypass_the_constructor_guard(module, name):
    assert_no_builtin_facts(analyze(module, 'ordinary_' + name), name, 'value')


@pytest.mark.parametrize('entry,name,parameter', [
    ('local_assignment', 'dict', 'kwargs'), ('late_assignment', 'dict', 'kwargs'),
    ('local_import', 'tuple', 'args'), ('local_definition', 'list', 'args'),
    ('local_class', 'dict', 'kwargs'), ('parameter', 'dict', 'kwargs'),
    ('except_binding', 'tuple', 'args'), ('outer.captured', 'dict', 'kwargs'),
    ('nonlocal_outer.captured', 'tuple', 'args'), ('late_outer.captured', 'list', 'args'),
    ('definition_default', 'dict', 'kwargs')])
def test_locals_and_lexical_captures_are_not_builtin_names(entry, name, parameter):
    assert_no_builtin_facts(analyze('locals', entry), name, parameter)


@pytest.mark.parametrize('entry,name,parameter', [
    ('mapping_call', 'dict', 'kwargs'), ('tuple_call', 'tuple', 'args')])
def test_unknown_builtin_namespace_cannot_prove_a_protocol(entry, name, parameter):
    assert_no_builtin_facts(analyze('namespace', entry), name, parameter)


@pytest.mark.parametrize('entry,name,parameter', [
    ('mapping_call', 'dict', 'kwargs'), ('tuple_call', 'tuple', 'args')])
def test_definition_evaluations_can_shadow_a_builtin(entry, name, parameter):
    assert_no_builtin_facts(analyze('evaluations', entry), name, parameter)


def test_lambda_body_bindings_do_not_shadow_the_outer_module():
    result = analyze('lambda_scope', 'mapping_call')
    assert result.find_calls(callee_name='dict')[0].target_status == 'local_container_protocol'
    assert result.trace_parameter('kwargs')['return_paths']


@pytest.mark.parametrize('entry,name,parameter', [
    ('mapping_call', 'dict', 'kwargs'), ('list_call', 'list', 'args'),
    ('tuple_call', 'tuple', 'args'),
    ('outer.inner', 'list', 'args'), ('Owner.method', 'dict', 'kwargs')])
def test_unshadowed_builtin_copies_keep_identity_and_current_dependencies(entry, name, parameter):
    result = analyze('positive', entry)
    call = result.find_calls(callee_name=name)[0]
    assert call.target_status == 'local_container_protocol'
    assert any(item['operation'] == 'copy' for item in call.effects)
    obj = next(item['container_object'] for item in call.result_sources if item.get('container_object'))
    assert obj['copied_from']
    assert obj['identity'] in ('shallow_copy', 'argument_alias')
    assert result.trace_parameter(parameter)['return_paths']


def test_unshadowed_builtin_return_summary_remains_available_without_container_shape():
    result = analyze('positive', 'ordinary_sequence')
    call = result.find_calls(callee_name='tuple')[0]
    assert call.target_status == 'python_protocol'
    assert result.trace_parameter('value')['return_paths']
    assert not any(value.get('container_object') for value in call.result_sources)


def test_unshadowed_copy_does_not_confuse_identity_or_restore_cleared_contents():
    assert analyze('positive', 'local_copy').trace_parameter('kwargs')['return_paths']
    assert not analyze('positive', 'cleared_copy').trace_parameter('kwargs')['return_paths']


def test_repeated_queries_do_not_share_builtin_name_proofs_between_modules():
    analyzer = FlowAnalyzer(project_root=ROOT)
    original = analyze('positive', 'mapping_call', analyzer).to_dict()
    assert_no_builtin_facts(analyze('shadow_repro', 'run', analyzer), 'dict', 'kwargs')
    assert analyze('positive', 'mapping_call', analyzer).to_dict() == original


@pytest.mark.parametrize('module,entry,name,status', [
    ('positive', 'mapping_call', 'dict', 'confirmed_builtin'),
    ('positive', 'global_read', 'dict', 'confirmed_builtin'),
    ('positive', 'outer.inner', 'list', 'confirmed_builtin'),
    ('positive', 'Owner.method', 'dict', 'confirmed_builtin'),
    ('module_if', 'mapping_call', 'dict', 'source_binding'),
    ('locals', 'parameter', 'dict', 'source_binding'),
    ('locals', 'outer.captured', 'dict', 'source_binding'),
    ('locals', 'nonlocal_outer.captured', 'tuple', 'source_binding'),
    ('global_writes', 'mapping_call', 'dict', 'source_binding'),
    ('wildcard', 'mapping_call', 'dict', 'unconfirmed'),
    ('namespace', 'mapping_call', 'dict', 'unconfirmed')])
def test_builtin_name_predicate_distinguishes_proof_binding_and_uncertainty(module, entry, name, status):
    analyzer = FlowAnalyzer(project_root=ROOT)
    analyzer._index()
    target = analyzer._definition_index.find(module, entry)[0]
    assert analyzer._builtin_name_status(*target, name) == status


def test_empty_or_runtime_capture_binding_blocks_a_static_builtin_proof():
    analyzer = FlowAnalyzer(project_root=ROOT)
    analyzer._index()
    target = analyzer._definition_index.find('positive', 'mapping_call')[0]
    assert analyzer._builtin_name_status(*target, 'dict', {'dict': []}) == 'source_binding'
    assert analyzer._builtin_name_status(*target, 'dict') == 'confirmed_builtin'
