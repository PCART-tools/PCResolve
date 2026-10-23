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


def test_literal_alias_decorator_records_generated_setter_names(tmp_path):
    source = '''from functools import partial, wraps
def define_aliases(alias_d, cls=None):
    if cls is None:
        return partial(define_aliases, alias_d)
    def make_alias(name):
        @wraps(getattr(cls, name))
        def method(self, *args, **kwargs):
            return getattr(self, name)(*args, **kwargs)
        return method
    for prop, aliases in alias_d.items():
        exists = False
        for prefix in ['get_', 'set_']:
            if prefix + prop in vars(cls):
                exists = True
                for alias in aliases:
                    method = make_alias(prefix + prop)
                    method.__name__ = prefix + alias
                    method.__doc__ = 'Alias for ' + prefix + prop
                    setattr(cls, prefix + alias, method)
        if not exists:
            raise ValueError(prop)
    cls._alias_map = alias_d
    return cls
def fixed(allowed=0): return allowed
@define_aliases({'color': ['c']})
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
    def set_color(self, value): pass
def client(**kwargs): return Public(**kwargs)
'''
    path = tmp_path / 'example.py'
    path.write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    target, cls = analyzer._definition_index.find('example', 'Public', kind='class')[0]
    from pcresolve._class_decoration import constructor_decorations
    decorations = constructor_decorations(analyzer, (target, cls))
    assert decorations is not None
    decoration = decorations[0]
    assert decoration['identity_status'] == 'preserved'
    assert 'set_c' in decoration['attributes']
    assert 'set_bbox_transmuter' not in decoration['attributes']
    assert decoration['generated_class_members'][0]['attribute'] == 'set_c'


def test_source_singleton_metadata_decorator_preserves_a_class_constructor(tmp_path):
    (tmp_path / 'documentation.py').write_text('''import inspect
class Substitution:
    def __init__(self): self.params = {}
    def __call__(self, func):
        if func.__doc__:
            func.__doc__ = inspect.cleandoc(func.__doc__) % self.params
        return func
class ArtistPropertiesSubstitution(Substitution):
    def __call__(self, obj):
        super().__call__(obj)
        if isinstance(obj, type) and obj.__init__ != object.__init__:
            self(obj.__init__)
        return obj
interpd = ArtistPropertiesSubstitution()
''', encoding='utf-8')
    (tmp_path / 'entry.py').write_text('''import documentation
def fixed(allowed=0): return allowed
@documentation.interpd
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'Public'))
    binding = result.inputs['entry_binding']
    assert binding['status'] == 'source_bound'
    decoration, = binding['class_decorations']
    assert decoration['kind'] == 'source_metadata_instance_class_decoration'
    assert decoration['identity_status'] == 'preserved'
    assert decoration['metadata_attributes'] == ['__doc__']
    assert decoration['attributes'] == []
    assert result.find_calls(callee_name='fixed')


def test_replacing_source_singleton_metadata_decorator_keeps_constructor_unconfirmed(tmp_path):
    (tmp_path / 'documentation.py').write_text('''import inspect
class Substitution:
    def __init__(self): self.params = {}
    def __call__(self, func):
        if func.__doc__:
            func.__doc__ = inspect.cleandoc(func.__doc__) % self.params
        return func
class ArtistPropertiesSubstitution(Substitution):
    def __call__(self, obj):
        super().__call__(obj)
        if isinstance(obj, type) and obj.__init__ != object.__init__:
            self(obj.__init__)
        return type('Replacement', (), {})
interpd = ArtistPropertiesSubstitution()
''', encoding='utf-8')
    (tmp_path / 'entry.py').write_text('''import documentation
def fixed(allowed=0): return allowed
@documentation.interpd
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
''', encoding='utf-8')
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'Public'))
