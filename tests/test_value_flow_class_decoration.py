## @package tests.test_value_flow_class_decoration

import ast
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures/value_flow_class_decoration'


@pytest.mark.parametrize('name', ['Public', 'Derived'])
def test_bounded_identity_class_decoration_preserves_the_initializer(name):
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', name))
    binding = result.inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    assert binding['target']['qualname'] == 'Public.__init__'
    assert binding['class_decorations'][0]['attributes'] == ['cache', 'other_cache']
    assert binding['class_decorations'][0]['identity_status'] == 'preserved'
    assert binding['class_decorations'][0]['completion'] == 'normal_return_only'
    assert result.find_calls(callee_name='fixed')


def test_explicit_class_call_has_the_same_preservation_requirements():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'client'))
    call = result.find_calls(callee_name='Public')[0]
    assert call.constructor_bindings[0]['status'] == 'source_bound'
    assert call.constructor_bindings[0]['class_decorations']


@pytest.mark.parametrize('name', ['Replaced', 'Escaped', 'Rebound', 'Structural', 'Dynamic', 'Conditional'])
def test_class_decorator_outside_the_proven_grammar_keeps_the_boundary(name):
    analyzer = FlowAnalyzer(project_root=ROOT)
    try:
        result = analyzer.analyze(FunctionRef('cases', name))
    except ValueError:
        return
    assert result.inputs['entry_binding']['status'] == 'unconfirmed'
    assert not result.calls


def test_runtime_controls_separate_cache_writes_from_replaced_initializers():
    tree = ast.parse((ROOT / 'cases.py').read_text(encoding='utf-8'))
    selected = {'Public', 'Derived', 'Replaced', 'Escaped', 'Rebound', 'Structural', 'Conditional'}
    tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and not node.decorator_list
                 or isinstance(node, ast.ClassDef) and node.name in selected]

    def replacement():
        return type('Replacement', (), {'__init__': lambda self, **kwargs: None})

    values = {'factory': replacement, 'unknown': lambda: True,
              'opaque': lambda cls: setattr(cls, '__init__', lambda self, **kwargs: None)}
    exec(compile(tree, str(ROOT / 'cases.py'), 'exec'), values)
    for name in ('Public', 'Derived'):
        assert isinstance(values[name](allowed=1), values[name])
        with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
            values[name](old=1)
    for name in selected - {'Public', 'Derived'}:
        values[name](old=1)


def test_imported_decorator_hash_and_edited_source_are_not_lost(tmp_path):
    decorator = tmp_path / 'dec.py'
    decorator.write_text('def cache(cls):\n    cls.cache = True\n    return cls\n', encoding='utf-8')
    (tmp_path / 'entry.py').write_text('''from dec import cache
def fixed(allowed=0): return allowed
@cache
class Public:
    def __init__(self, **kw): fixed(**kw)
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    before = analyzer.analyze(FunctionRef('entry', 'Public'))
    snapshot = before.to_dict()
    assert str(decorator) in before.inputs['entry_binding']['source_hashes']
    decorator.write_text('def cache(cls):\n    cls.__init__ = lambda self, **kw: None\n    return cls\n',
                         encoding='utf-8')
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('entry', 'Public'))
    assert before.to_dict() == snapshot


def test_constructor_slot_proof_does_not_prove_ordinary_instance_attribute_protocols():
    result = FlowAnalyzer(project_root=ROOT).analyze(FunctionRef('cases', 'decorated'))
    summary = next(item for item in result.functions if item['function']['qualname'] == 'decorated')
    assert summary['decorator_effects'][0]['body_binding_status'] != 'preserved'
    tree = ast.parse((ROOT / 'cases.py').read_text(encoding='utf-8'))
    tree.body = [node for node in tree.body if getattr(node, 'name', '') in
                 ('fixed', 'Replace', 'descriptor', 'Document', 'decorated')]
    values = {}
    exec(compile(tree, str(ROOT / 'cases.py'), 'exec'), values)
    assert values['decorated'](old=1) == {'old': 1}
