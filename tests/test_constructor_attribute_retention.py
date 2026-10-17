## @package tests.test_constructor_attribute_retention

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def facts(tmp_path, source):
    (tmp_path / 'sample.py').write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'Entry'))
    return result, result.inputs['entry_binding'].get('retained_instance_attribute_stores', [])


def test_plain_source_constructor_proves_a_retained_attribute_store(tmp_path):
    result, stores = facts(tmp_path, '''class Entry:
    def __init__(self, **kwargs):
        self.value = kwargs.pop('legacy', 0)
''')
    assert len(stores) == 1
    fact = stores[0]
    assert fact['kind'] == 'retained_instance_attribute_store'
    assert fact['status'] == 'source_bound'
    assert fact['receiver'] == 'self' and fact['attribute'] == 'value'
    assert fact['retention_scope'] == 'normal_constructor_return_after_store'
    assert fact['runtime_store_confirmed'] is False
    assert fact['store_evidence']['lineno'] == 3
    assert fact['source_hashes'] == result.inputs['sha256']


def test_source_parent_and_later_method_preserve_an_unwritten_field(tmp_path):
    _, stores = facts(tmp_path, '''class Parent:
    def __init__(self):
        self.other = 0
class Entry(Parent):
    def __init__(self, **kwargs):
        super(Entry, self).__init__()
        self.value = kwargs.pop('legacy', 0)
        self.reset()
    def reset(self):
        if self.other == 0:
            self.operation = lambda x: x + self.value
        else:
            self.operation = lambda x: x - self.value
        self.other = 1
''')
    assert any(fact['attribute'] == 'value' for fact in stores)
    fact = next(fact for fact in stores if fact['attribute'] == 'value')
    assert {item['qualname'] for item in fact['checked_methods']} == {
        'Entry.__init__', 'Parent.__init__', 'Entry.reset'}


@pytest.mark.parametrize('extra', [
    '    def __setattr__(self, name, value): pass\n',
    '    def __getattribute__(self, name): return 0\n',
    '    __slots__ = ()\n',
    '    value = unknown_descriptor\n',
])
def test_nonplain_instance_protocol_does_not_prove_retention(tmp_path, extra):
    _, stores = facts(tmp_path, 'class Entry:\n' + extra + '''    def __init__(self, **kwargs):
        self.value = kwargs.pop('legacy', 0)
''')
    assert not stores


@pytest.mark.parametrize('tail', [
    '        self.value = 0\n',
    '        del self.value\n',
    '        mutate(self)\n',
    "        setattr(self, 'value', 0)\n",
    '        alias = self\n        alias.value = 0\n',
    '        self.reset()\n    def reset(self):\n        self.value = 0\n',
    '        self.reset()\n    def reset(self):\n        self.reset()\n',
    '        self.callback = lambda: self\n        external(self.callback)\n',
    '        self.reset = unknown\n        self.reset()\n',
    '        return 1\n',
    '        self.callback = lambda: self\n'
    '        alias = self.callback\n        external(alias)\n',
    '        self.abort()\n    def abort(self):\n        raise ValueError()\n',
    "        peek = locals\n        peek()['self'].value = 0\n",
    "        from builtins import locals as peek\n        peek()['self'].value = 0\n",
    "        import inspect\n        inspect.currentframe().f_locals['self'].value = 0\n",
])
def test_later_writes_receiver_escape_and_open_dispatch_keep_retention_unproven(tmp_path, tail):
    _, stores = facts(tmp_path, '''class Entry:
    def __init__(self, **kwargs):
        self.value = kwargs.pop('legacy', 0)
''' + tail)
    assert not any(fact['attribute'] == 'value' for fact in stores)


def test_visible_class_mutation_invalidates_the_store_protocol(tmp_path):
    _, stores = facts(tmp_path, '''class Entry:
    def __init__(self, **kwargs):
        self.value = kwargs.pop('legacy', 0)
Entry.__setattr__ = unknown
''')
    assert not stores


def test_reading_a_source_descriptor_does_not_prove_unrelated_retention(tmp_path):
    _, stores = facts(tmp_path, '''class Descriptor:
    def __get__(self, instance, owner):
        instance.value = 0
        return None
class Entry:
    other = Descriptor()
    def __init__(self, **kwargs):
        self.value = kwargs.pop('legacy', 0)
        self.other
''')
    assert not stores


def test_explicit_super_class_argument_cannot_be_a_shadowing_parameter(tmp_path):
    _, stores = facts(tmp_path, '''class Parent:
    def __init__(self):
        self.other = 0
class Entry(Parent):
    def __init__(self, Entry=None, **kwargs):
        self.value = kwargs.pop('legacy', 0)
        super(Entry, self).__init__()
''')
    assert not stores
