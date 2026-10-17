import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def query(tmp_path, body):
    (tmp_path / 'example.py').write_text('class Entry:\n    def __init__(self, **kw):\n' + body)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('example', 'Entry.__init__'))
    return result.functions[0]['mapping_attribute_transfers']


def test_constructor_capture_store_is_only_an_observation_obligation(tmp_path):
    fact = query(tmp_path, '        self.options = kw\n        external(self)\n')[0]
    assert fact['kind'] == 'mapping_attribute_transfer'
    assert fact['status'] == 'requires_observation'
    assert fact['parameter'] == 'kw'
    assert fact['receiver'] == 'self' and fact['attribute'] == 'options'
    assert fact['store_completed'] is False
    assert fact['returned_instance_retention_proven'] is False
    assert fact['source_hash']


@pytest.mark.parametrize('body', [
    '        self.options = dict(kw)\n',
    '        self.options = kw\n        external(kw)\n',
    '        alias = kw\n        self.options = alias\n',
    '        if external():\n            self.options = kw\n',
    '        other.options = kw\n',
    "        self.options = kw\n        kw['x'] = 1\n",
    '        def nested():\n            self.options = kw\n',
])
def test_copy_alias_escape_nested_scope_and_conditional_store_are_excluded(tmp_path, body):
    assert not query(tmp_path, body)
