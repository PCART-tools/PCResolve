## @package tests.test_class_callable_decoration

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SUPPORT = '''class Document:
    def __init__(self, text='documentation'):
        self.text = text
    def __call__(self, function):
        function.__doc__ = self.text
        return function
'''


def analyze(tmp_path, support=SUPPORT, decorator='Document()', body=''):
    (tmp_path / 'support.py').write_text(support, encoding='utf-8')
    (tmp_path / 'entry.py').write_text('from support import Document\n'
        'def fixed(allowed=0): return allowed\nclass Entry:\n    @' + decorator
        + '\n    def __init__(self, **kwargs): fixed(**kwargs)\n' + body, encoding='utf-8')
    return FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'Entry'))


def test_closed_callable_decorator_can_preserve_a_constructor_body(tmp_path):
    result = analyze(tmp_path)
    binding = result.inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    assert str(tmp_path / 'support.py') in binding['source_hashes']
    assert 'source_function_namespace_preservation' in binding['assumptions']
    assert result.find_calls(callee_name='fixed')


def test_closed_callable_decoration_has_an_independent_runtime_control(tmp_path, monkeypatch):
    analyze(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    values = runpy.run_path(str(tmp_path / 'entry.py'))
    assert values['Entry'].__init__.__doc__ == 'documentation'
    values['Entry'](allowed=1)
    with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
        values['Entry'](old=1)


@pytest.mark.parametrize('statement', [
    'function.__code__ = replacement.__code__',
    'opaque(function)',
    'function.__defaults__ = (1,)',
])
def test_unproved_callable_decorator_keeps_constructor_unconfirmed(tmp_path, statement):
    result = analyze(tmp_path, SUPPORT.replace('function.__doc__ = self.text', statement))
    assert result.inputs['entry_binding']['status'] == 'unconfirmed'
    assert not result.calls


def test_other_decorated_member_must_also_preserve_class_namespace_formation(tmp_path):
    result = analyze(tmp_path, body='''    @Document()
    def unused(self): return None
''')
    assert result.inputs['entry_binding']['status'] == 'source_bound'


def test_closed_source_factory_uses_the_same_complete_namespace_proof(tmp_path):
    result = analyze(tmp_path, support='''def Document(text='documentation'):
    def decorate(function):
        function.__doc__ = text
        return function
    return decorate
''')
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    assert str(tmp_path / 'support.py') in result.inputs['entry_binding']['source_hashes']
