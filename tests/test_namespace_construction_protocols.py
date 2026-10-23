## @package tests.test_namespace_construction_protocols

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = '''import contextlib
def fixed(allowed=0): return allowed
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
    def get_value(self): return self.value
    def set_value(self, value): self.value = value
    value = property(get_value, set_value)
    @contextlib.contextmanager
    def temporary(self):
        opaque(self)
        yield self
'''


def analyze(root, text=SOURCE):
    (root / 'example.py').write_text(text, encoding='utf-8')
    return FlowAnalyzer(project_root=root).analyze(FunctionRef('example', 'Public'))


def assert_open(root, text=SOURCE):
    assert analyze(root, text).inputs['entry_binding']['status'] == 'unconfirmed'


def test_native_property_and_contextmanager_formation_do_not_execute_accessors(tmp_path):
    result = analyze(tmp_path)
    binding = result.inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    assert 'builtin_property_namespace_construction' in binding['assumptions']
    assert 'stdlib_contextmanager_function_construction' in binding['assumptions']


def test_contextmanager_from_import_alias_is_supported(tmp_path):
    text = SOURCE.replace('import contextlib', 'from contextlib import contextmanager as managed')
    text = text.replace('@contextlib.contextmanager', '@managed')
    assert analyze(tmp_path, text).inputs['entry_binding']['status'] == 'source_bound'


@pytest.mark.parametrize('old,new', [
    ('property(get_value, set_value)', 'property(opaque(), set_value)'),
    ('property(get_value, set_value)', 'property(opaque, set_value)'),
    ('property(get_value, set_value)', 'property(get_value, set_value, doc=opaque())'),
    ('    value = property', '    get_value = opaque\n    value = property'),
    ('    value = property', '    property = opaque\n    value = property'),
    ('    def get_value', '    @opaque\n    def get_value'),
    ('@contextlib.contextmanager', '@contextlib.contextmanager()'),
    ('@contextlib.contextmanager', '@opaque'),
    ('    @contextlib.contextmanager', '    contextlib = opaque\n    @contextlib.contextmanager'),
])
def test_open_binding_or_evaluation_does_not_gain_namespace_certainty(tmp_path, old, new):
    assert_open(tmp_path, SOURCE.replace(old, new))


@pytest.mark.parametrize('tail', [
    'contextlib.contextmanager = opaque',
    "setattr(contextlib, 'contextmanager', opaque)",
    'saved = contextlib.contextmanager\nsaved.__code__ = opaque',
    'opaque(contextlib)',
    "__import__('contextlib').contextmanager = opaque",
    "import importlib\nimportlib.import_module('contextlib').contextmanager = opaque",
])
def test_mutated_or_escaped_standard_decorator_stays_open(tmp_path, tail):
    assert_open(tmp_path, SOURCE + '\n' + tail + '\n')


def test_source_contextlib_replacement_is_not_the_standard_protocol(tmp_path):
    (tmp_path / 'contextlib.py').write_text('def contextmanager(fn): return opaque\n')
    assert_open(tmp_path)


def test_selected_contextmanager_body_is_not_authorized_by_namespace_formation(tmp_path):
    (tmp_path / 'example.py').write_text(SOURCE)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('example', 'Public.temporary'))
    assert any(item['reason'] == 'decorator_effect_unconfirmed' for item in result.boundaries)
