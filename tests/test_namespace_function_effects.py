## @package tests.test_namespace_function_effects

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from tests.flow_test_support import set_decorator_effect_limit
import pcresolve.flow.analyzer as flow
import pcresolve.flow.analysis.proof_context as flow_proof_context


def analyze(tmp_path, decorator_body, *, member_prefix='', class_prefix=''):
    (tmp_path / 'sample.py').write_text('def decorate(fn):\n' + decorator_body + '''
class Entry:
    def __init__(self, **kwargs):
        pass
''' + class_prefix + '    @decorate\n' + member_prefix + '''    def unused(self):
        raise AssertionError('Deferred body')
''', encoding='utf-8')
    return FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'Entry'))


@pytest.mark.parametrize('body', [
    '    return fn\n',
    '    fn.__doc__ = "Updated documentation"\n    return fn\n',
    '    if fn.__doc__:\n        fn.__doc__ = "Updated documentation"\n    return fn\n',
])
def test_preserved_plain_source_decoration_can_form_a_class_namespace(tmp_path, body):
    binding = analyze(tmp_path, body).inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    assert 'source_function_namespace_preservation' in binding['assumptions']
    assert binding['runtime_target_confirmed'] is False
    assert str(tmp_path / 'sample.py') in binding['source_hashes']


@pytest.mark.parametrize('body,options', [
    ('    external(fn)\n    return fn\n', {}),
    ('    fn.__defaults__ = (1,)\n    return fn\n', {}),
    ('    fn.__code__ = replacement.__code__\n    return fn\n', {}),
    ('    def wrapper(): return 1\n    return wrapper\n', {}),
    ('    return fn\n', {'class_prefix': '    decorate = 0\n'}),
    ('    return fn\n', {'member_prefix': '    @opaque\n'}),
])
def test_unmodeled_or_changed_function_decoration_stays_unconfirmed(tmp_path, body, options):
    assert analyze(tmp_path, body, **options).inputs['entry_binding']['status'] == 'unconfirmed'


@pytest.mark.parametrize('body,expected', [
    ('    fn.__doc__ = "Changed documentation"\n    return fn\n', 'source_bound'),
    ('    unknown(fn)\n    return fn\n', 'unconfirmed'),
    ('    fn.__defaults__ = (1,)\n    return fn\n', 'unconfirmed'),
])
def test_constructor_requires_its_own_execution_preservation(tmp_path, body, expected):
    (tmp_path / 'sample.py').write_text('def decorate(fn):\n' + body + '''
class Entry:
    @decorate
    def __init__(self, **kwargs):
        pass
''', encoding='utf-8')
    binding = FlowAnalyzer(project_root=tmp_path).analyze(
        FunctionRef('sample', 'Entry')).inputs['entry_binding']
    assert binding['status'] == expected
    if expected == 'unconfirmed':
        assert any(issue['reason'] == 'constructor_initialization_unconfirmed'
                   for issue in binding['issues'])


def test_preservation_does_not_survive_an_exhausted_query_or_changed_source(tmp_path, monkeypatch):
    analyze(tmp_path, '    return fn\n')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    entry = FunctionRef('sample', 'Entry')
    assert analyzer.analyze(entry).inputs['entry_binding']['status'] == 'source_bound'
    with monkeypatch.context() as patch:
        set_decorator_effect_limit(patch, 0)
        assert analyzer.analyze(entry).inputs['entry_binding']['status'] == 'unconfirmed'
    assert analyzer.analyze(entry).inputs['entry_binding']['status'] == 'source_bound'
    analyze(tmp_path, '    opaque(fn)\n    return fn\n')
    analyzer.add_files([tmp_path / 'sample.py'])
    assert analyzer.analyze(entry).inputs['entry_binding']['status'] == 'unconfirmed'
