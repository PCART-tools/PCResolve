## @package tests.test_value_flow_callable_instances
#  Source candidates for module-level constructor-backed callable objects.

import json
from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow_callable_instances'


def analyze(qualname):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='consumer', qualname=qualname))


def test_imported_module_callable_instance_has_call_target_and_constructor_sources():
    result = analyze('accepted')
    call = result.find_calls(callee_name='nv.validator')[0]
    assert call.target.module == 'provider'
    assert call.target.qualname == 'Validator.__call__'
    assert call.target_status == 'callable_instance_candidate'
    assert [item['qualname'] for item in call.target_candidates] == ['Validator.__call__']
    fact = call.callable_instance_evidence
    assert fact['qualified_name'] == 'provider.validator'
    assert fact['instance_type']['qualname'] == 'Validator'
    assert 'validator = Validator' in fact['assignment']['source_text']
    defaults = next(item for item in fact['constructor_arguments']
                    if item['parameter'] == 'defaults')
    assert defaults['source']['kind'] == 'module_symbol'
    assert defaults['source']['qualified_name'] == 'provider.DEFAULTS'
    assert any('DEFAULTS["mode"]' in item['source_text']
               for item in defaults['source_assignments'])
    method = next(item for item in fact['constructor_arguments']
                  if item['parameter'] == 'method')
    assert method['source'] == {'kind': 'literal', 'value': 'kwargs'}
    assert any(source['source'] == 'kwargs'
               for argument in call.argument_sources
               for source in argument['sources'])
    assert any(item.get('call_id') == call.id
               and item['reason'] == 'dynamic_callable_instance_override_possible'
               for item in result.boundaries)
    json.dumps(result.to_dict())


def test_direct_import_alias_retains_constructor_and_call_evidence():
    result = analyze('accepted_import_alias')
    call = result.find_calls(callee_name='aliased_validator')[0]
    assert call.target.qualname == 'Validator.__call__'
    assert call.callable_instance_evidence['qualified_name'] == 'provider.validator'
    assert call.callable_instance_evidence['call']['source_text'].startswith(
        'aliased_validator(')


def test_callable_instance_negative_cases_preserve_boundaries():
    causes = {'reassigned': 'multiple_bindings',
              'unknown_factory': 'constructor_unavailable',
              'dynamically_modified': 'dynamic_method_write',
              'conditionally_bound': 'conditional_binding',
              'class_name_rebound': 'constructor_unavailable'}
    for entry, cause in causes.items():
        result = analyze(entry)
        call = result.find_calls(callee_name='nv.' + (
            'unknown' if entry == 'unknown_factory' else
            'modified' if entry == 'dynamically_modified' else
            'conditional' if entry == 'conditionally_bound' else
            'class_rebound' if entry == 'class_name_rebound' else entry))[0]
        assert call.target is None, entry
        assert call.target_candidates == [], entry
        assert call.target_status == 'receiver_unresolved', entry
        assert any(item.get('call_id') == call.id
                   and item['reason'] == 'module_callable_instance_unresolved'
                   and item['cause'] == cause for item in result.boundaries)

    for entry, name in [('unknown_parameter', 'receiver'),
                        ('shadowed_alias', 'nv.validator')]:
        result = analyze(entry)
        call = result.find_calls(callee_name=name)[0]
        assert call.target is None
        assert call.target_candidates == []
        assert call.target_status in ('definition_unavailable', 'receiver_unresolved')
