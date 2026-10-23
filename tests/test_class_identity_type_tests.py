## @package tests.test_class_identity_type_tests

import ast
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve._class_identity import identity_decorations
from pcresolve._class_type_tests import native_class_operand


SOURCE = '''def decorate(cls):
    opaque(cls)
    return cls
@decorate
class Public:
    def __init__(self, **kwargs): pass
def check(value): return isinstance(value, Public)
'''


def prepare(root, text=SOURCE):
    (root / 'example.py').write_text(text, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    target = analyzer._definition_index.find('example', 'Public', kind='class')[0]
    check = analyzer._definition_index.find('example', 'check')[0]
    call = next(node for node in ast.walk(check[1]) if isinstance(node, ast.Call))
    return analyzer, target, check, call


def test_normal_return_identity_does_not_claim_decorator_effect_preservation(tmp_path):
    analyzer, target, check, call = prepare(tmp_path)
    facts = identity_decorations(analyzer, target)
    assert len(facts) == 1
    fact = facts[0]
    assert fact['identity_status'] == 'preserved'
    assert fact['body_effects'] == 'unmodeled'
    assert fact['completion'] == 'normal_return_only'
    assert fact['runtime_identity_confirmed'] is False
    assert native_class_operand(analyzer, check[0], call, {})
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    assert not any(owner == target[0] and reason == 'visible_class_escape'
                   for owner, _, reason, _, _ in writes)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_identity_can_hold_when_the_decorator_replaces_the_constructor(tmp_path):
    text = SOURCE.replace('    opaque(cls)',
        '    cls.__init__ = lambda self, **kwargs: setattr(self, "received", kwargs)')
    analyzer, target, check, call = prepare(tmp_path, text)
    assert identity_decorations(analyzer, target)
    assert native_class_operand(analyzer, check[0], call, {})
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))
    namespace = runpy.run_path(str(tmp_path / 'example.py'))
    assert namespace['Public'](old=1).received == {'old': 1}


@pytest.mark.parametrize('old,new', [
    ('return cls', 'return opaque'),
    ('    opaque(cls)', '    cls = opaque'),
    ('    opaque(cls)', '    if unknown: return opaque'),
    ('    opaque(cls)', '    del cls'),
    ('    opaque(cls)', '    class cls: pass'),
    ('    opaque(cls)', '    def cls(): pass'),
    ('    opaque(cls)', '    def change():\n        nonlocal cls\n        cls = opaque\n    change()'),
    ('def decorate(cls):', 'async def decorate(cls):'),
    ('    opaque(cls)', '    yield cls'),
    ('@decorate\nclass Public:', '@opaque\nclass Public:'),
    ('class Public:', 'class Public(metaclass=opaque):'),
])
def test_replacement_rebinding_and_open_class_protocols_are_not_native(tmp_path, old, new):
    analyzer, target, check, call = prepare(tmp_path, SOURCE.replace(old, new))
    assert not native_class_operand(analyzer, check[0], call, {})


def test_deferred_helper_returns_do_not_replace_the_outer_identity_return(tmp_path):
    text = SOURCE.replace('    opaque(cls)', '    def later(): return opaque\n    opaque(cls)')
    analyzer, target, check, call = prepare(tmp_path, text)
    assert identity_decorations(analyzer, target)
    assert native_class_operand(analyzer, check[0], call, {})


def test_literal_partial_class_factory_keeps_only_its_identity_claim(tmp_path):
    text = SOURCE.replace('def decorate(cls):', '''import functools
def decorate(label, cls=None):
    if cls is None:
        return functools.partial(decorate, label)''')
    text = text.replace('@decorate\nclass Public:', "@decorate('label')\nclass Public:")
    analyzer, target, check, call = prepare(tmp_path, text)
    fact = identity_decorations(analyzer, target)[0]
    assert fact['factory_binding']['class_parameter'] == 'cls'
    assert native_class_operand(analyzer, check[0], call, {})


def test_source_callable_instance_has_the_same_distinct_identity_obligation(tmp_path):
    text = SOURCE.replace('def decorate(cls):\n    opaque(cls)\n    return cls', '''class Documentation:
    def __call__(self, cls):
        opaque(cls)
        return cls
decorate = Documentation()''')
    analyzer, target, check, call = prepare(tmp_path, text)
    assert identity_decorations(analyzer, target)[0]['decorator']['qualname'] == 'Documentation.__call__'
    assert native_class_operand(analyzer, check[0], call, {})


def test_class_identity_guard_is_not_reused_after_source_changes(tmp_path):
    analyzer, target, _, _ = prepare(tmp_path)
    assert identity_decorations(analyzer, target)
    (tmp_path / 'example.py').write_text(SOURCE.replace('return cls', 'return opaque'))
    analyzer._index()
    target = analyzer._definition_index.find('example', 'Public', kind='class')[0]
    assert identity_decorations(analyzer, target) is None


@pytest.mark.parametrize('mutation', [
    'decorate.__class__ = Other',
    "setattr(decorate, '__class__', Other)",
    'alias = decorate\nalias.__class__ = Other',
    'opaque(decorate)',
    'alias = decorate\nopaque(alias)',
    "opaque(globals()['decorate'])",
    'decorate.__class__.__call__ = replacement',
    'opaque(decorate.__class__)',
    "setattr(decorate.__getattribute__('__class__'), '__call__', replacement)",
    'opaque(decorate.__call__)',
])
def test_a_source_callable_instance_can_change_its_class_before_decoration(tmp_path, mutation):
    text = SOURCE.replace('def decorate(cls):\n    opaque(cls)\n    return cls', '''class Documentation:
    def __call__(self, cls): return cls
class Other:
    def __call__(self, cls): return opaque
decorate = Documentation()
''' + mutation)
    analyzer, target, check, call = prepare(tmp_path, text)
    assert identity_decorations(analyzer, target) is None
    assert not native_class_operand(analyzer, check[0], call, {})


def test_pattern_binding_can_replace_a_decorator_parameter(tmp_path):
    if not hasattr(ast, 'Match'):
        pytest.skip('Pattern matching source needs Python 3.10+')
    text = SOURCE.replace('    opaque(cls)', '    match opaque:\n        case cls: return cls')
    analyzer, target, check, call = prepare(tmp_path, text)
    assert identity_decorations(analyzer, target) is None
    assert not native_class_operand(analyzer, check[0], call, {})


def test_a_nested_class_decorator_cannot_reuse_a_shadowed_module_binding(tmp_path):
    text = SOURCE.replace('@decorate\nclass Public:\n    def __init__(self, **kwargs): pass', '''class Container:
    decorate = opaque
    @decorate
    class Public:
        def __init__(self, **kwargs): pass''').replace('isinstance(value, Public)',
                                                              'isinstance(value, Container.Public)')
    (tmp_path / 'example.py').write_text(text)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    check = analyzer._definition_index.find('example', 'check')[0]
    call = next(node for node in ast.walk(check[1]) if isinstance(node, ast.Call))
    assert not native_class_operand(analyzer, check[0], call, {})


def test_exhausted_identity_work_does_not_release_a_partial_proof(tmp_path):
    analyzer, target, check, call = prepare(tmp_path)
    analyzer._class_identity_steps = 0
    assert identity_decorations(analyzer, target) is None
    assert not native_class_operand(analyzer, check[0], call, {})


def test_a_callable_method_cannot_expose_its_receiver_to_unknown_code(tmp_path):
    text = SOURCE.replace('def decorate(cls):\n    opaque(cls)\n    return cls', '''class Documentation:
    def __call__(self, cls):
        opaque(self)
        return cls
decorate = Documentation()''')
    analyzer, target, check, call = prepare(tmp_path, text)
    assert identity_decorations(analyzer, target) is None
    assert not native_class_operand(analyzer, check[0], call, {})
