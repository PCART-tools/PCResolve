## @package tests.test_value_flow_text_decorators

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def fact(tmp_path, import_text='import inspect', call='inspect.cleandoc(func.__doc__)', suffix=''):
    (tmp_path / 'cases.py').write_text(import_text + '\n'
        'def decorate(func):\n'
        '    func.__doc__ = ' + call + '\n'
        '    return func\n'
        '@decorate\n'
        'def entry(**kwargs):\n'
        '    """Source documentation."""\n'
        '    return fixed(**kwargs)\n'
        'def fixed(allowed=None): pass\n' + suffix)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'entry'))
    return next(row for row in result.functions if row['function']['qualname'] == 'entry')[
        'decorator_effects'][0]


@pytest.mark.parametrize('import_text,call', [
    ('import inspect', 'inspect.cleandoc(func.__doc__)'),
    ('from inspect import cleandoc as clean', 'clean(func.__doc__)'),
    ('from textwrap import dedent', 'dedent(func.__doc__)'),
])
def test_exact_string_normalization_preserves_decorated_body(tmp_path, import_text, call):
    proof = fact(tmp_path, import_text, call)
    assert proof['identity_status'] == proof['body_binding_status'] == 'preserved'
    assert not proof['boundaries']
    assert 'standard_library_text_protocols_hold' in proof['assumptions']
    effects = [e for e in proof['effects'] if e.get('protocol') == 'stdlib_text_normalization']
    assert len(effects) == 1
    assert effects[0]['input_shapes'] == [['str']]
    assert effects[0]['output_shape'] == 'str'


@pytest.mark.parametrize('call,suffix', [
    ('inspect.cleandoc(func)', ''),
    ('inspect.cleandoc(unknown)', ''),
    ('inspect.cleandoc(func.__doc__, 1)', ''),
    ('inspect.cleandoc(func.__doc__)', '\ninspect.cleandoc = replacement\n'),
    ('inspect.cleandoc(func.__doc__)', '\ninspect = replacement\n'),
])
def test_unproven_input_binding_and_namespace_do_not_gain_text_protocol(tmp_path, call, suffix):
    proof = fact(tmp_path, call=call, suffix=suffix)
    assert proof['body_binding_status'] != 'preserved'


def test_local_import_shadow_is_not_the_standard_library(tmp_path):
    (tmp_path / 'inspect.py').write_text('def cleandoc(value):\n    mutate()\n    return value\n')
    assert fact(tmp_path)['body_binding_status'] != 'preserved'
