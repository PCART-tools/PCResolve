## @package tests.test_class_type_test_escapes

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = '''class Base:
    def __init_subclass__(cls): cls.marker = True
class Public(Base):
    def __init__(self, **kwargs): self.update(kwargs)
    def update(self, props):
        for key, value in props.items():
            setter = getattr(self, f'set_{key}', None)
            if not callable(setter): raise AttributeError(key)
            setter(value)
    def set_allowed(self, value): self.allowed = value
'''


def inspect(root, tail):
    (root / 'example.py').write_text(SOURCE + '\n' + tail + '\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    return analyzer, [item for item in writes if item[0].qualname == 'Public']


@pytest.mark.parametrize('tail', [
    'isinstance(value, Public)',
    'issubclass(value, Public)',
    'def check(value): return isinstance(value, Public)',
    'def check(value): return issubclass(value, (Public, str))',
    'external(lambda value: isinstance(value, Public))',
    'external([isinstance(value, Public) for value in values])',
    'from builtins import range\nisinstance(value, Public)',
])
def test_native_type_tests_do_not_expose_the_class_argument(tmp_path, tail):
    analyzer, writes = inspect(tmp_path, tail)
    assert not writes
    result = analyzer.analyze(FunctionRef('example', 'Public'), max_depth=2)
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    assert any(function.get('fresh_mapping_member_checks') for function in result.functions)


@pytest.mark.parametrize('tail', [
    'def check(value, isinstance): return isinstance(value, Public)',
    'isinstance = opaque\nisinstance(value, Public)',
    'def check(value):\n    isinstance = opaque\n    return isinstance(value, Public)',
    'def outer(isinstance):\n    def check(value): return isinstance(value, Public)'
    '\n    return check',
    'external(lambda isinstance: isinstance(value, Public))',
    'external([isinstance(value, Public) for isinstance in values])',
    'import builtins\nbuiltins.isinstance = opaque\nisinstance(value, Public)',
    'saved = isinstance\nsaved.__self__.isinstance = opaque\nisinstance(value, Public)',
    'isinstance.__self__.isinstance = opaque\nisinstance(value, Public)',
    'isinstance(opaque(Public), Public)',
    'isinstance(value, opaque(Public))',
    'isinstance(value, (Public, unknown))',
    'opaque(Public)',
    'external(lambda value=Public: isinstance(value, str))',
])
def test_shadowing_unknown_protocols_and_nested_argument_escapes_are_retained(tmp_path, tail):
    _, writes = inspect(tmp_path, tail)
    assert any(item[2] == 'visible_class_escape' for item in writes)


@pytest.mark.parametrize('prefix', [
    '@opaque\n',
    '',
])
def test_unproved_metaclasses_are_not_native_type_predicates(tmp_path, prefix):
    text = SOURCE.replace('class Public(Base):', prefix + 'class Public(Base, metaclass=opaque):')
    (tmp_path / 'example.py').write_text(text + '\nisinstance(value, Public)\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated and any(item[0].qualname == 'Public' for item in writes)


def test_a_class_decorator_may_replace_the_metaclass_even_without_a_keyword(tmp_path):
    text = SOURCE.replace('class Public(Base):', '@opaque\nclass Public(Base):')
    (tmp_path / 'example.py').write_text(text + '\nisinstance(value, Public)\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    assert any(item[0].qualname == 'Public'
               for item in analyzer._class_binding_writes(include_escapes=True)[0])


def test_method_values_cannot_masquerade_as_class_arguments(tmp_path):
    _, writes = inspect(tmp_path, 'saved = Public.update\nisinstance(value, saved)')
    assert any(item[2] == 'visible_class_escape' for item in writes)


def test_a_source_metaclass_callback_can_replace_the_constructor(tmp_path):
    text = '''def replacement(self, **kwargs): self.received = kwargs
class Meta(type):
    def __instancecheck__(cls, value):
        cls.__init__ = replacement
        return True
class Public(metaclass=Meta):
    def __init__(self): pass
isinstance(object(), Public)
'''
    path = tmp_path / 'example.py'
    path.write_text(text, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    assert any(item[0].qualname == 'Public' and item[2] == 'visible_class_escape'
               for item in analyzer._class_binding_writes(include_escapes=True)[0])
    assert runpy.run_path(str(path))['Public'](old=1).received == {'old': 1}


def test_type_predicate_guards_are_rebuilt_after_source_changes(tmp_path):
    analyzer, writes = inspect(tmp_path, 'isinstance(value, Public)')
    assert not writes
    (tmp_path / 'example.py').write_text(SOURCE + '\nisinstance = opaque\n'
                                       'isinstance(value, Public)\n', encoding='utf-8')
    analyzer._index()
    assert any(item[0].qualname == 'Public'
               for item in analyzer._class_binding_writes(include_escapes=True)[0])


@pytest.mark.parametrize('binding,name', [('Public', 'Public'), ('Public as Alias', 'Alias')])
def test_a_unique_local_source_import_supplies_the_exact_class(tmp_path, binding, name):
    (tmp_path / 'example.py').write_text(SOURCE, encoding='utf-8')
    (tmp_path / 'other.py').write_text('def check(value):\n'
        f'    from example import {binding}\n    return isinstance(value, {name})\n',
        encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    assert not any(item[0].qualname == 'Public'
                   for item in analyzer._class_binding_writes(include_escapes=True)[0])


@pytest.mark.parametrize('prefix', ['Public = opaque', 'Public = Public.update',
                                   'if value:\n        Public = opaque'])
def test_a_rebound_local_import_does_not_retain_its_original_class_type(tmp_path, prefix):
    (tmp_path / 'example.py').write_text(SOURCE, encoding='utf-8')
    (tmp_path / 'other.py').write_text('def check(value):\n'
        '    from example import Public\n    ' + prefix
        + '\n    return isinstance(value, Public)\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    assert any(item[0].qualname == 'Public'
               for item in analyzer._class_binding_writes(include_escapes=True)[0])


def test_a_local_custom_class_cannot_borrow_a_same_named_global_metaclass(tmp_path):
    (tmp_path / 'other.py').write_text('''class Meta(type):
    def __instancecheck__(cls, value): return opaque(cls)
class Foreign(metaclass=Meta): pass
''', encoding='utf-8')
    (tmp_path / 'example.py').write_text(SOURCE + '''
def check(value):
    from other import Foreign as Public
    return isinstance(value, Public)
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    assert any(item[0].qualname == 'Foreign' and item[2] == 'visible_class_escape'
               for item in analyzer._class_binding_writes(include_escapes=True)[0])


def test_documentation_copy_retains_an_unproved_current_function_binding(tmp_path):
    analyzer, writes = inspect(tmp_path, 'class Other:\n'
        '    def method(self): pass\n'
        '    method.__doc__ = Public.set_allowed.__doc__')
    # The declaration's function type alone is insufficient: the base hook can
    # replace the class slot before this later documentation copy executes.
    assert any(item[2] == 'visible_class_escape' for item in writes)


@pytest.mark.parametrize('tail', [
    'Public.set_allowed = opaque\ntext = Public.set_allowed.__doc__',
    'opaque(Public.set_allowed)\ntext = Public.set_allowed.__doc__',
    'opaque(Public.set_allowed.__globals__)',
    'opaque(Public.set_allowed.__dict__)',
])
def test_function_metadata_projection_keeps_mutation_and_capability_exposures(tmp_path, tail):
    _, writes = inspect(tmp_path, tail)
    assert writes


def test_root_class_function_documentation_copy_has_a_native_input_proof(tmp_path):
    source = SOURCE.replace('class Public(Base):', 'class Public:') + '''
class Other:
    def method(self): pass
    method.__doc__ = Public.set_allowed.__doc__
'''
    (tmp_path / 'example.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    assert not [item for item in writes if item[0].qualname == 'Public']


@pytest.mark.parametrize('mutation', [
    'Public.set_allowed = opaque',
    'Public.set_allowed.__doc__ = opaque',
    'opaque(Public)',
    'opaque(Public.set_allowed)',
])
def test_root_class_metadata_read_cannot_remove_other_mutation_or_escape_evidence(tmp_path, mutation):
    source = SOURCE.replace('class Public(Base):', 'class Public:') + '\n' + mutation + '''
class Other:
    def method(self): pass
    method.__doc__ = Public.set_allowed.__doc__
'''
    (tmp_path / 'example.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    assert [item for item in writes if item[0].qualname == 'Public']


def test_a_type_check_helper_can_expose_class_metadata_through_a_foreign_metaclass(tmp_path):
    source = '''def fixed(allowed=0): return allowed
class Public:
    def __init__(self): pass

def replacement(cls, **kwargs): return {'received': kwargs}
class ForeignMeta(type):
    def __getattribute__(cls, name):
        if name == '__module__':
            Public.__new__ = replacement
        return super().__getattribute__(name)
class Foreign(metaclass=ForeignMeta): pass

def type_name(tp):
    return tp.__qualname__ if tp.__module__ == 'builtins' else tp.__module__ + '.' + tp.__qualname__
def check_instance(types, **kwargs):
    for name, value in kwargs.items():
        if not isinstance(value, types):
            raise TypeError(type_name(types) + ' not ' + type_name(type(value)))
try:
    check_instance(Public, item=Foreign())
except TypeError:
    pass
'''
    path = tmp_path / 'example.py'
    path.write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    assert any(item[0].qualname == 'Public' for item in writes)
    namespace = runpy.run_path(str(path))
    assert namespace['Public'](old=1) == {'received': {'old': 1}}


def test_dynamic_classmethod_replacement_prevents_scalar_metadata_projection(tmp_path):
    source = '''def fixed(allowed=0): return allowed
def allocate(cls, **kwargs): return {'received': kwargs}
class Descriptor:
    def __get__(self, instance, owner):
        class Data:
            __doc__ = owner
        return Data()
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
    def method(self):
        """Initially native text."""
    @classmethod
    def seed(cls): setattr(cls, 'method', Descriptor())
def expose(candidate): candidate.__new__ = allocate
Public.seed()
expose(Public.method.__doc__)
'''
    path = tmp_path / 'example.py'
    path.write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    assert any(item[0].qualname == 'Public' for item in writes)
    namespace = runpy.run_path(str(path))
    assert namespace['Public'](old=1) == {'received': {'old': 1}}


def test_a_bounded_unrelated_classmethod_write_preserves_the_scalar_read(tmp_path):
    source = SOURCE.replace('class Public(Base):', '''class Public:
    @classmethod
    def seed(cls): cls.marker = True''') + '''
Public.seed()
class Other:
    def method(self): pass
    method.__doc__ = Public.set_allowed.__doc__
'''
    (tmp_path / 'example.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    writes, truncated = analyzer._class_binding_writes(include_escapes=True)
    assert not truncated
    assert not [item for item in writes if item[0].qualname == 'Public']
