## @package tests.test_regression_return_shape_protocol
#  Local return alternatives must retain receiver protocol evidence.

import ast
from pathlib import Path

import pytest

from pcresolve import analyze_project
from pcresolve.single_file import SingleFileAnalyzer
from pcresolve.sources import PythonShape, SourceSet


FACTORIES = Path(__file__).parent / 'fixtures' / 'mixed_return_shapes' / 'factories.py'


def _owner(tmp_path, source, expression="value.get('key')"):
    (tmp_path / 'factories.py').write_text(
        FACTORIES.read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path / 'main.py').write_text(source, encoding='utf-8')
    calls = analyze_project(str(tmp_path)).all_api_calls
    matched = [call for call in calls
               if call.expression == expression]
    assert len(matched) == 1
    return matched[0].top_library


@pytest.mark.parametrize('fallback', [
    'return 42', 'return None', 'return', 'return opaque()',
    'return []', 'return ()',
])
@pytest.mark.parametrize('reverse', [False, True])
def test_every_return_branch_must_support_method(tmp_path, fallback, reverse):
    first, second = ('return {}', fallback)
    if reverse:
        first, second = second, first
    source = '''
from dependency import opaque
def build(flag):
    if flag:
        %s
    %s
def consume(value):
    return value.get('key')
consume(build(opaque()))
''' % (first, second)
    assert _owner(tmp_path, source) == 'unknown'


@pytest.mark.parametrize('argument, expected', [
    ('choose(opaque())', 'unknown'),
    ('identity({})', 'python'),
    ('identity(42)', 'unknown'),
    ('forward({})', 'python'),
    ('forward(42)', 'unknown'),
    ('forward(choose(opaque()))', 'unknown'),
    ('recursive(opaque())', 'unknown'),
    ('Factory().dictionary()', 'python'),
    ('Factory().build(opaque())', 'unknown'),
])
def test_cross_file_return_protocol_uses_exact_context(tmp_path, argument, expected):
    source = '''
from dependency import opaque
from factories import choose, identity, forward, recursive, Factory
def consume(value):
    return value.get('key')
identity(42)
forward(42)
consume(%s)
''' % argument
    assert _owner(tmp_path, source) == expected


def test_all_dictionary_returns_keep_protocol(tmp_path):
    assert _owner(tmp_path, '''
from dependency import opaque
def build(flag):
    if flag:
        return {}
    options = {}
    options['key'] = 1
    return options
def consume(value):
    return value.get('key')
consume(build(opaque()))
''') == 'python'


def test_return_summary_retains_scalar_and_dictionary_shapes():
    tracer = SingleFileAnalyzer(module_name='factories')
    tracer.visit(ast.parse(FACTORIES.read_text(encoding='utf-8')))
    summary = tracer.module_cg.functions['choose'].return_values
    assert isinstance(summary, SourceSet)
    assert set(summary.sources) == {PythonShape('dict'), PythonShape('int')}


def test_implicit_none_return_is_not_dropped(tmp_path):
    assert _owner(tmp_path, '''
from dependency import opaque
def build(flag):
    if flag:
        return {}
def consume(value):
    return value.get('key')
consume(build(opaque()))
''') == 'unknown'


def test_exhaustive_if_return_has_no_implicit_none(tmp_path):
    assert _owner(tmp_path, '''
from dependency import opaque
def build(flag):
    if flag:
        return {}
    else:
        return {'key': 1}
def consume(value):
    return value.get('key')
consume(build(opaque()))
''') == 'python'


def test_nested_functions_do_not_share_return_values(tmp_path):
    assert _owner(tmp_path, '''
def outer():
    def build():
        return {}
    return build()
def unrelated():
    def build():
        return 42
    return build()
def consume(value):
    return value.get('key')
unrelated()
consume(outer())
''') == 'python'


def test_supported_method_on_different_python_shapes(tmp_path):
    assert _owner(tmp_path, '''
from dependency import opaque
def build(flag):
    if flag:
        return {}
    return []
def consume(value):
    return value.copy()
consume(build(opaque()))
''', 'value.copy()') == 'python'


def test_builtin_scalar_return_is_not_a_dictionary(tmp_path):
    assert _owner(tmp_path, '''
def consume(value):
    return value.get('key')
consume(int())
''') == 'unknown'


@pytest.mark.parametrize('method, expected', [
    ('bit_length', 'python'), ('numerator', 'unknown'),
])
def test_scalar_protocol_checks_the_builtin_descriptor(tmp_path, method, expected):
    expression = 'value.%s()' % method
    assert _owner(tmp_path, '''
def consume(value):
    return %s
consume(int())
''' % expression, expression) == expected


def test_constructor_initializer_return_is_not_instance_shape(tmp_path):
    assert _owner(tmp_path, '''
class Bag:
    def __init__(self):
        self.data = {}
    def get(self, key):
        return self.data[key]
def consume(value):
    return value.get('key')
consume(Bag())
''') == 'local'


def test_branch_assignment_does_not_erase_missing_receiver(tmp_path):
    assert _owner(tmp_path, '''
from dependency import opaque
def build():
    return {}
def consume(value):
    return value.get('key')
def invoke(flag):
    if flag:
        options = None
    else:
        options = build()
    consume(options)
invoke(opaque())
''') == 'unknown'


def test_builtin_method_result_keeps_element_shape(tmp_path):
    assert _owner(tmp_path, '''
def consume(text):
    for value in text:
        value.isalpha()
text = 'abc '
consume(text.strip())
''', 'value.isalpha()') == 'python'


@pytest.mark.parametrize('unpack, expected', [(True, 'pandas'), (False, 'unknown')])
def test_tuple_result_is_not_confused_with_unpacked_items(tmp_path, unpack, expected):
    assignment = ('value, other = build(pd.DataFrame())' if unpack
                  else 'value = build(pd.DataFrame())')
    assert _owner(tmp_path, '''
import pandas as pd
def build(frame):
    first = frame[:1]
    second = frame[1:]
    return first, second
def consume(value):
    return value.get('key')
%s
consume(value)
''' % assignment) == expected
