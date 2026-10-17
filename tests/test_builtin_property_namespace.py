## @package tests.test_builtin_property_namespace

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def analyze(tmp_path, members, prefix=''):
    (tmp_path / 'sample.py').write_text(prefix + '''
class Entry:
    def __init__(self, **kwargs):
        pass
''' + members, encoding='utf-8')
    return FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'Entry'))


@pytest.mark.parametrize('prefix,decorator', [
    ('', 'property'),
    ('import builtins as native\n', 'native.property'),
    ('from builtins import property as descriptor\n', 'descriptor'),
])
def test_builtin_property_creation_does_not_execute_the_getter(tmp_path, prefix, decorator):
    result = analyze(tmp_path, '    @' + decorator + '''
    def unused(self, property=None):
        raise AssertionError('Not executed while constructing Entry')
''', prefix)
    binding = result.inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    assert 'builtin_property_namespace_construction' in binding['assumptions']
    assert binding['runtime_target_confirmed'] is False


def test_local_getter_setter_and_deleter_preserve_property_construction(tmp_path):
    result = analyze(tmp_path, '''    @property
    def value(self):
        return self._value
    @value.setter
    def value(self, value):
        self._value = value
    @value.deleter
    def value(self):
        del self._value
''')
    assert result.inputs['entry_binding']['status'] == 'source_bound'


@pytest.mark.parametrize('prefix,members', [
    ('property = replacement\n', '    @property\n    def value(self): return 1\n'),
    ('', '    property = 0\n    @property\n    def value(self): return 1\n'),
    ('', '    @property()\n    def value(self): return 1\n'),
    ('', '    @unknown.setter\n    def value(self, value): pass\n'),
    ('', '    @property\n    def value(self): return 1\n'
         '    value = 0\n    @value.setter\n    def value(self, value): pass\n'),
    ('', '    @property\n    def value(self, default=effect()): return 1\n'),
    ('import builtins\nbuiltins.property = replacement\n',
     '    @property\n    def value(self): return 1\n'),
    ('import builtins\nalias = builtins\nalias.property = replacement\n',
     '    @property\n    def value(self): return 1\n'),
    ("__builtins__['property'] = replacement\n",
     '    @property\n    def value(self): return 1\n'),
    ("__import__('builtins').property = replacement\n",
     '    @property\n    def value(self): return 1\n'),
    ("import builtins\nnamespace = getattr(builtins, '__dict__')\n"
     "namespace['property'] = replacement\n",
     '    @property\n    def value(self): return 1\n'),
    ("namespace = __import__('builtins').__dict__\nnamespace['property'] = replacement\n",
     '    @property\n    def value(self): return 1\n'),
    ("import builtins\nsetter = builtins.__setattr__\nsetter('property', replacement)\n",
     '    @property\n    def value(self): return 1\n'),
    ("getter = __import__('builtins').__getattribute__\n"
     "getter('__dict__')['property'] = replacement\n",
     '    @property\n    def value(self): return 1\n'),
    ("from builtins import __dict__ as namespace\nnamespace['property'] = replacement\n",
     '    @property\n    def value(self): return 1\n'),
    ("from builtins import *\n",
     '    @property\n    def value(self): return 1\n'),
])
def test_open_or_shadowed_property_namespace_does_not_gain_a_binding(tmp_path, prefix, members):
    result = analyze(tmp_path, members, prefix)
    assert result.inputs['entry_binding']['status'] == 'unconfirmed'


def test_later_class_binding_does_not_shadow_an_earlier_property_decorator(tmp_path):
    result = analyze(tmp_path, '''    @property
    def value(self): return 1
    property = 0
''')
    assert result.inputs['entry_binding']['status'] == 'source_bound'


def test_property_premises_refresh_after_a_source_edit(tmp_path):
    analyze(tmp_path, '    @property\n    def value(self): return 1\n')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    before = analyzer.analyze(FunctionRef('sample', 'Entry'))
    assert before.inputs['entry_binding']['status'] == 'source_bound'
    (tmp_path / 'patch.py').write_text('import builtins\nbuiltins.property = replacement\n',
                                      encoding='utf-8')
    analyzer.add_files([tmp_path / 'patch.py'])
    after = analyzer.analyze(FunctionRef('sample', 'Entry'))
    assert after.inputs['entry_binding']['status'] == 'unconfirmed'


def test_builtin_inventory_reads_do_not_expose_the_mutable_module(tmp_path):
    result = analyze(tmp_path, '    @property\n    def value(self): return 1\n', '''import builtins
def inspect_names(other):
    return [name for name in dir(builtins)
            if getattr(builtins, name) != other and hasattr(builtins, name)]
''')
    assert result.inputs['entry_binding']['status'] == 'source_bound'


def test_readonly_import_projection_does_not_expose_the_namespace(tmp_path):
    result = analyze(tmp_path, '    @property\n    def value(self): return 1\n',
                     "native_bytes = __import__('builtins').bytes\n")
    assert result.inputs['entry_binding']['status'] == 'source_bound'


@pytest.mark.parametrize('expression', [
    '(lambda dir: dir(builtins))(unknown)',
    '[dir(builtins) for dir in [unknown]]',
    '(lambda getattr: getattr(builtins, "property"))(unknown)',
])
def test_shadowed_inventory_read_callees_do_not_gain_builtin_permissions(tmp_path, expression):
    result = analyze(tmp_path, '    @property\n    def value(self): return 1\n',
                     'import builtins\ndef expose():\n    return ' + expression + '\n')
    assert result.inputs['entry_binding']['status'] == 'unconfirmed'
