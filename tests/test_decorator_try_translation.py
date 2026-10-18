## @package tests.test_decorator_try_translation

import ast
from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.effect_facts import builtin_exception_translation


SOURCE = (Path(__file__).parent / 'fixtures' /
          'value_flow_decorator_try_translation' / 'sample.py').read_text(encoding='utf-8')


def analyze(root, text=SOURCE):
    path = root / 'sample.py'
    path.write_text(text, encoding='utf-8')
    result = FlowAnalyzer(project_root=root).analyze(FunctionRef('sample', 'entry'))
    return result.functions[0]['decorator_effects'][0], path


def test_exception_only_translation_preserves_the_normal_decorated_body(tmp_path):
    fact, path = analyze(tmp_path)
    assert fact['body_binding_status'] == 'preserved'
    assert fact['identity_status'] == 'preserved'
    assert not fact['boundaries']
    raised = next(effect for effect in fact['effects']
                  if effect['target'] == 'KeyError')
    translation = raised['exception_translation']
    assert translation['caught_types'] == ['ValueError']
    assert translation['exception_name'] == 'error'
    assert translation['cause_kind'] == 'caught_exception'
    assert translation['completion'] == 'exceptional_exit_only'
    assert translation['runtime_exception_observed'] is False
    runtime = runpy.run_path(str(path))
    assert runtime['entry'].__doc__ == 'entry'
    assert runtime['entry'](allowed=1) == 1
    with pytest.raises(TypeError):
        runtime['entry'](old=1)

    def fail():
        pass

    fail.__qualname__ = 'entry_missing'
    with pytest.raises(KeyError) as failure:
        runtime['Document']()(fail)
    assert type(failure.value.__cause__) is ValueError


@pytest.mark.parametrize('handler', [
    'except (ValueError, TypeError) as error:\n            raise KeyError(label) from error',
    'except ValueError:\n            raise KeyError(label)',
    'except ValueError as error:\n            raise KeyError(label) from None',
])
def test_finite_builtin_handlers_and_explicit_context_suppression(tmp_path, handler):
    text = SOURCE.replace('except ValueError as error:\n            raise KeyError(label) from error',
                          handler)
    fact, _ = analyze(tmp_path, text)
    assert fact['body_binding_status'] == 'preserved'


@pytest.mark.parametrize('old,new', [
    ('except ValueError as error:', 'except CustomError as error:'),
    ('raise KeyError(label) from error', 'return func'),
    ('raise KeyError(label) from error', 'raise KeyError(label) from opaque'),
    ('raise KeyError(label) from error', 'raise KeyError(error) from error'),
    ('raise KeyError(label) from error', 'raise KeyError(func) from error'),
    ('raise KeyError(label) from error', 'raise CustomError(label) from error'),
    ('raise KeyError(label) from error', 'raise KeyError(func.__doc__) from error'),
    ('raise KeyError(label) from error', 'raise KeyError(label) from error\n        finally:\n            func.__code__ = opaque'),
    ('raise KeyError(label) from error', 'func.__code__ = opaque\n            raise KeyError(label) from error'),
    ('func.__doc__ = normalize(label)', 'label = normalize(label)'),
    ('func.__doc__ = normalize(label)', 'opaque(func)'),
    ('func.__doc__ = normalize(label)', 'func.__code__ = opaque'),
])
def test_unproved_handlers_and_try_effects_do_not_approve_the_body(tmp_path, old, new):
    fact, _ = analyze(tmp_path, SOURCE.replace(old, new))
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']


@pytest.mark.parametrize('prefix', ['ValueError = opaque\n',
                                  'import builtins\nbuiltins.ValueError = opaque\n',
                                  'import builtins\nbuiltins.KeyError = opaque\n'])
def test_exception_handler_types_require_preserved_builtin_bindings(tmp_path, prefix):
    fact, _ = analyze(tmp_path, prefix + SOURCE)
    assert fact['body_binding_status'] != 'preserved'


def test_real_query_inside_a_translating_try_keeps_its_inner_boundary(tmp_path):
    text = SOURCE.replace('func.__doc__ = normalize(label)',
                          'result, = [cls for cls in opaque() if cls.__name__ == label]')
    fact, _ = analyze(tmp_path, text)
    assert fact['body_binding_status'] != 'preserved'
    assert not any(item['reason'] == 'decorator_statement_unsupported'
                   and item['evidence']['source_text'].startswith('try:')
                   for item in fact['boundaries'])
    assert fact['boundaries']


def test_shared_translation_shape_is_syntax_not_a_binding_proof():
    source = 'try:\n    pass\nexcept ValueError as error:\n    raise KeyError(label) from error\n'
    handler = ast.parse(source).body[0].handlers[0]
    shape = builtin_exception_translation(handler)
    assert shape == {'caught_types': ['ValueError'], 'exception_name': 'error',
                     'raised_type': 'KeyError', 'cause_kind': 'caught_exception',
                     'argument_names': ['label']}
    handler.type = ast.Name(id='CustomError', ctx=ast.Load())
    assert builtin_exception_translation(handler) is None
