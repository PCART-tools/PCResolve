## @package tests.test_class_lambda_retention

import pytest

from pcresolve import FlowAnalyzer


SOURCE = '''class Entry:
    def method(self, value=0): return value
'''


def writes(root, tail):
    (root / 'example.py').write_text(SOURCE + tail, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    effects, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    return [effect for effect in effects if effect[0].qualname == 'Entry']


@pytest.mark.parametrize('tail', [
    'callback = lambda receiver: Entry.method(receiver)\nexternal(callback)\n',
    'holder.callback = lambda receiver: Entry.method(receiver)\n',
    'external(lambda value: isinstance(value, Entry))\n',
    'external(lambda Entry: Entry.method())\n',
])
def test_a_future_global_method_lookup_does_not_retain_the_class_value(tmp_path, tail):
    assert not writes(tmp_path, tail)


@pytest.mark.parametrize('tail', [
    'external(lambda: Entry)\n',
    'external(lambda: opaque(Entry))\n',
    'external(lambda default=Entry: 0)\n',
    'external(lambda default=opaque(Entry): 0)\n',
    'def factory():\n    held = Entry\n    return lambda value: held.method(value)\n',
    'def factory():\n    from example import Entry as held\n'
    '    return lambda value: held.method(value)\n',
    'def factory():\n    from example import Entry\n'
    '    def inner(): return lambda value: Entry.method(value)\n'
    '    return inner\n',
    'external(lambda isinstance: isinstance(value, Entry))\n',
    'external(lambda: (lambda: opaque(Entry)))\n',
])
def test_returned_classes_real_closure_cells_defaults_and_future_escapes_are_retained(tmp_path, tail):
    assert any(effect[2] == 'visible_class_escape' for effect in writes(tmp_path, tail))


def test_a_later_lambda_body_write_is_still_a_class_namespace_write(tmp_path):
    effects = writes(tmp_path, 'callback = lambda: setattr(Entry, "__init__", opaque)\n')
    assert any(effect[1:3] == ('__init__', 'visible_dynamic_attribute_write') for effect in effects)
