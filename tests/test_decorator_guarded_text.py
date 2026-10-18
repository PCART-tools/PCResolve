## @package tests.test_decorator_guarded_text

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = '''class Text(dict):
    def __missing__(self, key):
        if not key.endswith(':doc'):
            raise KeyError(key)
        name = key[:-len(':doc')]
        return self.setdefault(key, name)
class Document:
    def __init__(self): self.params = Text()
    def __call__(self, func):
        if func.__doc__:
            func.__doc__ = func.__doc__ % self.params
        return func
def fixed(allowed=0): return allowed
@Document()
def entry(**kwargs):
    """%(section:doc)s"""
    return fixed(**kwargs)
'''


def analyze(tmp_path, source=SOURCE):
    path = tmp_path / 'sample.py'
    path.write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'entry'))
    return result.functions[0]['decorator_effects'][0], path


def test_guarded_document_callback_preserves_the_source_function_on_normal_return(tmp_path):
    fact, path = analyze(tmp_path)
    assert fact['body_binding_status'] == 'preserved'
    assert fact['identity_status'] == 'preserved'
    assert not fact['boundaries']
    assert {'str.endswith', 'len', 'str.__getitem__', 'KeyError'} <= {
        effect['target'] for effect in fact['effects'] if isinstance(effect['target'], str)}
    runtime = runpy.run_path(str(path))
    assert runtime['entry'].__doc__ == 'section'
    with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
        runtime['entry'](old=1)
    with pytest.raises(KeyError):
        runtime['Text']()['unsupported']


@pytest.mark.parametrize('expression', ['key[:3]', 'key[1:]', 'key[::2]', 'key[::-1]',
                                       "key[:-len(':doc')]", 'key[1:-1:2]'])
def test_only_exact_builtin_integer_slice_bounds_are_used(tmp_path, expression):
    fact, _ = analyze(tmp_path, SOURCE.replace("key[:-len(':doc')]", expression))
    assert fact['body_binding_status'] == 'preserved'


@pytest.mark.parametrize('old,new', [
    ("key[:-len(':doc')]", 'key[::0]'),
    ("key[:-len(':doc')]", 'key[:unknown]'),
    ("key[:-len(':doc')]", 'key[:True]'),
    ("key.endswith(':doc')", 'key.endswith(unknown)'),
    ('raise KeyError(key)', 'raise CustomError(key)'),
    ('raise KeyError(key)', 'raise KeyError(key) from unknown'),
    ('raise KeyError(key)', 'raise KeyError(func)'),
])
def test_unproved_data_or_exception_operations_keep_a_boundary(tmp_path, old, new):
    fact, _ = analyze(tmp_path, SOURCE.replace(old, new))
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']


@pytest.mark.parametrize('name', ['len', 'KeyError'])
def test_shadowed_text_and_exception_builtins_do_not_gain_protocol_facts(tmp_path, name):
    fact, _ = analyze(tmp_path, f'{name} = unknown\n' + SOURCE)
    assert fact['body_binding_status'] != 'preserved'


@pytest.mark.parametrize('prefix', [
    'import builtins\nbuiltins.len = unknown\n',
    'import builtins as original\noriginal.KeyError = unknown\n',
    'import builtins\nsetattr(builtins, "len", unknown)\n',
    'import builtins\nalias = builtins\n',
    'import builtins\nbuiltins.isinstance = unknown\n',
    'from builtins import len as length\nlength.__self__.__dict__["len"] = unknown\n',
    'from builtins import len as length\nunknown(length)\n',
])
def test_visible_builtin_namespace_mutation_or_escape_cannot_use_the_models(tmp_path, prefix):
    fact, _ = analyze(tmp_path, prefix + SOURCE)
    assert fact['body_binding_status'] != 'preserved'
    assert any(boundary['reason'] == 'decorator_builtin_namespace_unproven'
               for boundary in fact['boundaries'])
