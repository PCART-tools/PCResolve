## @package tests.test_value_flow_conditional_constructor

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

SOURCE = '''from typing import Optional, Union, Dict
class Request:
    defaults = dict(timeout=1)
    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
    @property
    def headers(self) -> str:
        return self._headers
    @headers.setter
    def headers(self, value: Union[str, bytes]):
        self._headers = value
def fetch(request, **kwargs):
    if not isinstance(request, Request):
        return Request(url=request, **kwargs)
'''


def query(tmp_path, source=SOURCE, conditional=False):
    (tmp_path / 'cases.py').write_text(source)
    return FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef('cases', 'fetch'), conditional_source_state=conditional)


def test_conditional_signature_reference_retains_unconfirmed_binding(tmp_path):
    ordinary = query(tmp_path)
    before = ordinary.to_dict()
    conditioned = query(tmp_path, conditional=True)
    call = conditioned.find_calls(callee_name='Request')[0]
    assert call.constructor_bindings[0]['status'] == 'unconfirmed'
    fact = call.conditional_source_bindings[0]
    assert fact['kind'] == 'conditional_constructor_signature'
    assert fact['scope'] == 'signature_only'
    assert fact['runtime_target_confirmed'] is False
    assert fact['source_hashes'] == conditioned.inputs['sha256']
    assert fact['conditions'] == call.conditions
    assert any(value.get('kind') == 'source_constructor_lookup' for value in fact['conditions'])
    assert not any(value.get('argument') == {'constructor_instance': True}
                   for value in call.argument_sources)
    assert ordinary.to_dict() == before
    assert not ordinary.find_calls(callee_name='Request')[0].conditional_source_bindings


@pytest.mark.parametrize('source', [
    SOURCE.replace('defaults = dict(timeout=1)', 'defaults = unknown()'),
    SOURCE.replace('defaults = dict(timeout=1)', 'dict = unknown\n    defaults = dict(timeout=1)'),
    SOURCE + '\nRequest.__init__ = replacement\n',
    SOURCE.replace('class Request:', 'class Request(metaclass=Meta):'),
    SOURCE.replace('if not isinstance(request, Request):',
                   'escape(Request)\n    if not isinstance(request, Request):'),
    SOURCE.replace('def fetch(request, **kwargs):', 'def fetch(request, isinstance, **kwargs):'),
    SOURCE.replace('@property', '@unknown'),
    SOURCE.replace('Optional[Dict[str, str]]', 'Unknown[str]'),
    SOURCE.replace('Optional[Dict[str, str]]', 'change()'),
    SOURCE.replace('def __init__(self, url:', 'def __new__(self, url:'),
])
def test_unsafe_definition_lookup_and_escape_do_not_gain_a_conditional_signature(tmp_path, source):
    result = query(tmp_path, source, conditional=True)
    assert not any(call.conditional_source_bindings for call in result.find_calls(callee_name='Request'))


def test_imported_class_uses_its_definition_scope_for_builtins(tmp_path):
    definition, caller = SOURCE.split('def fetch', 1)
    (tmp_path / 'model.py').write_text('dict = replacement\n' + definition)
    (tmp_path / 'cases.py').write_text('from model import Request\ndef fetch' + caller)
    result = FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef('cases', 'fetch'), conditional_source_state=True)
    assert not result.find_calls(callee_name='Request')[0].conditional_source_bindings
