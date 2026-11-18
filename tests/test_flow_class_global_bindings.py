## @package tests.test_flow_class_global_bindings

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def test_class_method_global_rebinding_invalidates_a_nominal_source_callable(tmp_path):
    source = tmp_path / 'entry.py'
    source.write_text('''def fixed(allowed=0): return allowed
class Cache(dict):
    def __missing__(self, key):
        global fixed
        fixed = lambda **kwargs: kwargs
        return 'text'
Cache()['doc']
def client(**kwargs): return fixed(**kwargs)
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'client'))
    call = result.find_calls(callee_name='fixed')[0]
    assert call.target is None
    assert call.target_status != 'resolved'
    assert any(boundary['reason'] == 'module_callable_binding_unconfirmed'
               and boundary['call_id'] == call.id and boundary['declarations']
               for boundary in result.boundaries)
    assert runpy.run_path(str(source))['client'](old=1) == {'old': 1}


@pytest.mark.parametrize('expression', ['fixed(**kwargs)', 'alias(**kwargs)'])
def test_imported_or_locally_aliased_global_does_not_recover_the_old_function(tmp_path, expression):
    (tmp_path / 'support.py').write_text('''def fixed(allowed=0): return allowed
class Changes:
    def update(self):
        global fixed
        fixed = lambda **kwargs: kwargs
''', encoding='utf-8')
    (tmp_path / 'entry.py').write_text('from support import fixed\n'
        'def client(**kwargs):\n    alias = fixed\n    return ' + expression + '\n', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'client'))
    assert result.find_calls(callee_name=expression.partition('(')[0])[0].target is None


@pytest.mark.parametrize('body', [
    'global fixed\nreturn fixed',
    'fixed = lambda **kwargs: kwargs\nreturn fixed',
    'global other\nother = 1',
])
def test_read_only_declaration_and_unrelated_local_writes_preserve_the_binding(tmp_path, body):
    source = tmp_path / 'entry.py'
    source.write_text('def fixed(allowed=0): return allowed\nclass Read:\n    def inspect(self):\n'
        + '\n'.join('        ' + line for line in body.splitlines())
        + '\ndef client(**kwargs): return fixed(**kwargs)\n', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'client'))
    assert result.find_calls(callee_name='fixed')[0].target.qualname == 'fixed'


@pytest.mark.parametrize('body', [
    'del fixed',
    'def fixed(**kwargs): return kwargs',
    'try:\n    raise ValueError()\nexcept ValueError as fixed:\n    pass',
    'local = lambda value=(fixed := lambda **kwargs: kwargs): None',
])
def test_class_global_writes_include_delete_definitions_handlers_and_default_evaluation(tmp_path, body):
    (tmp_path / 'entry.py').write_text('def fixed(allowed=0): return allowed\n'
        'class Changes:\n    def change(self):\n        global fixed\n'
        + '\n'.join('        ' + line for line in body.splitlines())
        + '\ndef client(**kwargs): return fixed(**kwargs)\n', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'client'))
    assert result.find_calls(callee_name='fixed')[0].target is None


def test_class_body_global_rebinding_cannot_recover_the_previous_definition(tmp_path):
    source = tmp_path / 'entry.py'
    source.write_text('''def fixed(allowed=0): return allowed
class Changes:
    global fixed
    fixed = lambda **kwargs: kwargs
def client(**kwargs): return fixed(**kwargs)
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'client'))
    assert result.find_calls(callee_name='fixed')[0].target is None
    assert runpy.run_path(str(source))['client'](old=1) == {'old': 1}
