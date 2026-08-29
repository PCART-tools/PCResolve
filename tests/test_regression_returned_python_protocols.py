## @package tests.test_regression_returned_python_protocols
#  Concrete Python shapes survive local returns without owner-only guesses.

from pathlib import Path

import pytest

from pcresolve import analyze_project
from pcresolve.cross_file import ProjectAnalyzer
from pcresolve.sources import InstanceMethod, PythonShape, UnknownSource


HELPERS = Path(__file__).parent / 'fixtures' / 'returned_python_protocols' / 'helpers.py'


def test_python_shape_owner_reentry_terminates_and_releases_guard(tmp_path, monkeypatch):
    analyzer = ProjectAnalyzer(str(tmp_path))
    source = InstanceMethod(UnknownSource('recursive receiver'), 'group')

    def candidates(module, receiver, tracers):
        assert analyzer._returned_python_shape(module, source, tracers) is None
        return ['unknown']

    monkeypatch.setattr(analyzer, '_origin_candidates', candidates)
    assert analyzer._returned_python_shape('main', source, {}) is None
    assert analyzer._returned_python_shape('main', source, {}) is None
    assert analyzer._returned_python_shape('main', PythonShape('str'), {}) == PythonShape('str')


def _analyze(tmp_path, source):
    (tmp_path / 'helpers.py').write_text(
        HELPERS.read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path / 'main.py').write_text(source, encoding='utf-8')
    return {call.expression: call.top_library
            for call in analyze_project(str(tmp_path)).all_api_calls
            if Path(call.file_path).name == 'main.py'}


@pytest.mark.parametrize('producer', [
    "split_parts('a|b')", "forward(' a|b ')",
    "identity(['a', 'b'])", "sliced(['a', 'b'])",
])
def test_local_return_iteration_keeps_string_items(tmp_path, producer):
    calls = _analyze(tmp_path, '''
from helpers import split_parts, forward, identity, sliced
for value in %s:
    value.upper()
''' % producer)
    assert calls['value.upper()'] == 'python'


@pytest.mark.parametrize('producer', [
    "clean(' abc ')", "identity('abc')", "sliced('abc')",
])
def test_return_protocol_survives_another_argument_edge(tmp_path, producer):
    calls = _analyze(tmp_path, '''
from helpers import clean, identity, sliced
def consume(value):
    value.upper()
consume(%s)
''' % producer)
    assert calls['value.upper()'] == 'python'


@pytest.mark.parametrize('producer', [
    'identity(42)', 'identity([])', 'mixed(opaque())',
    'recursive(opaque())', "identity(eval('runtime_value'))",
])
def test_unknown_or_incompatible_return_is_not_string(tmp_path, producer):
    calls = _analyze(tmp_path, '''
from helpers import identity, mixed, recursive
from dependency import opaque
def consume(value):
    value.upper()
consume(%s)
''' % producer)
    assert calls['value.upper()'] == 'unknown'


def test_same_function_different_calls_do_not_merge_shapes(tmp_path):
    calls = _analyze(tmp_path, '''
from helpers import identity, split_parts
identity(42)
split_parts(42)
for value in split_parts(identity('a|b')):
    value.upper()
''')
    assert calls['value.upper()'] == 'python'


def test_unknown_item_in_returned_list_is_not_python(tmp_path):
    calls = _analyze(tmp_path, '''
from helpers import identity
from dependency import opaque
for value in identity(['a', opaque()]):
    value.upper()
''')
    assert calls['value.upper()'] == 'unknown'


@pytest.mark.parametrize('values,owner', [("[' a ', 'b']", 'python'),
                                         ('[42]', 'unknown')])
def test_returned_method_uses_selected_parameter_item(tmp_path, values, owner):
    calls = _analyze(tmp_path, '''
def first(items):
    return items[0].strip()
def consume(value):
    value.upper()
consume(first(%s))
''' % values)
    assert calls['value.upper()'] == owner


@pytest.mark.parametrize('assignment,owner', [
    ('value = Template.parse(42).subst()', 'python'),
    ('value: object = Template.parse(42).subst()', 'python'),
    ('value = Template.parse(42).subst(); value = 42', 'unknown'),
    ('value = Template.parse(42).subst()\n    if flag:\n        value = 42', 'unknown'),
])
def test_assigned_local_method_return_preserves_call_context(tmp_path, assignment, owner):
    calls = _analyze(tmp_path, '''
class Template:
    @classmethod
    def parse(cls, body):
        return Template()
    def subst(self):
        return str(42)
def forward(flag):
    %s
    consume(value)
def consume(value):
    value.upper()
forward(True)
''' % assignment)
    assert calls['value.upper()'] == owner


def test_local_factory_returning_external_surface_is_not_local_receiver(tmp_path):
    calls = _analyze(tmp_path, '''
from bs4 import BeautifulSoup
class Parser:
    def soup(self):
        return BeautifulSoup('<p>ok</p>', 'html.parser')
    def run(self):
        value = self.soup().find('p')
        value.find_all('a')
Parser().run()
''')
    assert calls["value.find_all('a')"] == 'bs4'


@pytest.mark.parametrize('producer,owner', [
    ("clean(' abc ')", 'python'), ("identity(['abc'])", 'unknown'),
    ("identity(42)", 'unknown'),
])
def test_slice_of_parameter_from_local_return_keeps_protocol(tmp_path, producer, owner):
    calls = _analyze(tmp_path, '''
from helpers import clean, identity
def consume(text):
    value = text[1:]
    value.upper()
consume(%s)
''' % producer)
    assert calls['value.upper()'] == owner


@pytest.mark.parametrize('alternate,owner', [
    ("['fallback']", 'python'), ('[42]', 'unknown'),
    ('opaque()', 'unknown'),
])
def test_branch_return_keeps_literal_and_parameter_protocols(tmp_path, alternate, owner):
    calls = _analyze(tmp_path, '''
from dependency import opaque, flag
def split_parts(text):
    if flag:
        parts = text.split('|')
    else:
        parts = %s
    return parts
for value in split_parts('a|b'):
    value.upper()
''' % alternate)
    assert calls['value.upper()'] == owner
