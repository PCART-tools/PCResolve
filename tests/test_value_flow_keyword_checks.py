## @package tests.test_value_flow_keyword_checks

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

SOURCE = '''class Artist:
    def update(self, props):
        for k, v in props.items():
            func = getattr(self, f'set_{k}', None)
            if not callable(func):
                raise AttributeError(f'unknown property {k}')
            func(v)
'''


def query(tmp_path, source=SOURCE):
    (tmp_path / 'cases.py').write_text(source)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'Artist.update'))
    return result, result.functions[0].get('keyword_checks', [])


def test_validation_guard_is_a_runtime_obligation_not_a_static_rejection(tmp_path):
    result, checks = query(tmp_path)
    assert len(checks) == 1
    fact = checks[0]
    assert fact['kind'] == 'mapping_member_validation'
    assert fact['status'] == 'requires_observation'
    assert fact['mapping_parameter'] == 'props'
    assert fact['key_variable'] == 'k'
    assert fact['lookup_variable'] == 'func'
    assert fact['attribute_template'] == {'prefix': 'set_', 'suffix': ''}
    assert fact['exception'] == 'AttributeError'
    assert fact['runtime_rejection_confirmed'] is False
    assert fact['source_hash'] == result.inputs['sha256'][result.entry.file_path]
    assert any(b.get('reason') == 'receiver_unresolved' for b in result.boundaries)


@pytest.mark.parametrize('source', [
    SOURCE.replace('def update(self, props):', 'def update(self, props, getattr):'),
    SOURCE.replace('def update(self, props):', 'def update(self, props, callable):'),
    SOURCE.replace('def update(self, props):', 'def update(self, props, AttributeError):'),
    SOURCE.replace('getattr(self,', 'external(self,'),
    SOURCE.replace('if not callable(func):', 'if arbitrary(func):'),
    SOURCE.replace('raise AttributeError(', 'return AttributeError('),
])
def test_custom_or_unrelated_protocol_is_not_a_keyword_check(tmp_path, source):
    assert query(tmp_path, source)[1] == []


def test_nested_function_checks_are_not_attributed_to_the_outer_caller(tmp_path):
    source = 'def outer(props):\n    def nested(self, props):\n'
    source += '\n'.join('    ' + line for line in SOURCE.splitlines()[2:]) + '\n'
    (tmp_path / 'cases.py').write_text(source)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'outer'))
    assert result.functions[0].get('keyword_checks') == []
