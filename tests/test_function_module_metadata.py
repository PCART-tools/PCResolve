## @package tests.test_function_module_metadata

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = '''def set_module(module):
    def decorate(fn):
        fn.__module__ = module
        return fn
    return decorate
def fixed(allowed=0): return allowed
@set_module('public_api')
def public(**kwargs): return fixed(**kwargs)
'''


def analyze(root, text=SOURCE):
    (root / 'example.py').write_text(text, encoding='utf-8')
    return FlowAnalyzer(project_root=root).analyze(FunctionRef('example', 'public'))


@pytest.mark.parametrize('value,shape', [("'public_api'", 'str'), ('None', 'NoneType')])
def test_native_function_module_assignment_preserves_only_its_execution_binding(tmp_path, value, shape):
    result = analyze(tmp_path, SOURCE.replace("@set_module('public_api')", '@set_module(' + value + ')'))
    fact = next(item for item in result.functions if item['function']['qualname'] == 'public')[
        'decorator_effects'][0]
    assert fact['identity_status'] == fact['body_binding_status'] == 'preserved'
    assert not fact['boundaries']
    effect = next(item for item in fact['effects'] if item['target'] == 'input_function')
    assert effect['element_path'] == ['__module__']
    assert effect['impact'] == 'module_metadata'
    assert effect['protocol'] == 'builtin_function_module_attribute'
    assert effect['value_shapes'] == [shape]
    assert effect['execution_fields_unchanged'] is True
    assert effect['runtime_write_confirmed'] is False
    assert 'builtin_function_module_attribute' in fact['assumptions']


@pytest.mark.parametrize('old,new', [
    ('fn.__module__ = module', 'fn.__code__ = module'),
    ('fn.__module__ = module', 'fn.__defaults__ = module'),
    ('fn.__module__ = module', 'fn.__dict__ = module'),
    ("@set_module('public_api')", '@set_module(opaque)'),
    ("@set_module('public_api')", '@set_module(opaque())'),
    ("@set_module('public_api')", '@set_module(7)'),
    ('fn.__module__ = module', 'opaque(fn)\n        fn.__module__ = module'),
])
def test_module_metadata_does_not_authorize_other_slots_or_unknown_effects(tmp_path, old, new):
    result = analyze(tmp_path, SOURCE.replace(old, new))
    fact = next(item for item in result.functions if item['function']['qualname'] == 'public')[
        'decorator_effects'][0]
    assert fact['body_binding_status'] != 'preserved'
