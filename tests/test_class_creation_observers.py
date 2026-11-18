## @package tests.test_class_creation_observers

import runpy
import json

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = '''class Observer:
    def __init__(self, obj): self.obj = obj
    def names(self):
        return [name for name in dir(self.obj)
                if name.startswith('set_') and callable(getattr(self.obj, name))]
class Base:
    def __init_subclass__(cls):
        cls.names = Observer(cls).names()
class Public(Base):
    def __init__(self, **kwargs): fixed(**kwargs)
    def set_value(self, value): self.value = value

def fixed(allowed=0): return allowed
'''


def analyze(root, source=SOURCE):
    path = root / 'example.py'
    path.write_text(source, encoding='utf-8')
    return FlowAnalyzer(project_root=root).analyze(FunctionRef('example', 'Public')), path


def test_creation_binds_a_private_class_directory_observer(tmp_path):
    result, path = analyze(tmp_path)
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    query = hook['class_metadata_queries'][0]
    assert query['status'] == 'source_bound'
    assert query['query']['status'] == 'requires_native_class_metadata'
    assert query['input_binding']['phase'] == 'class_creation_entry'
    assert query['input_binding']['creation_dependency'] == 'source_class_creation_prefix'
    assert query['input_binding']['ancestor_creation_hooks'] == []
    json.dumps(hook)
    assert query['input_binding']['matching_members'][0]['attribute'] == 'set_value'
    assert set(query['assumptions']) <= set(hook['assumptions'])
    assert hook['attributes'] == ['names']
    assert runpy.run_path(str(path))['Public'].names == ['set_value']


@pytest.mark.parametrize('old,new', [
    ('self.obj = obj', 'self.obj = obj; opaque(obj)'),
    ('def set_value(self, value): self.value = value', 'set_value = opaque'),
    ('cls.names = Observer(cls).names()', 'cls.set_value = opaque\n        cls.names = Observer(cls).names()'),
    ('cls.names = Observer(cls).names()', 'cls.names = Observer(cls).names()\n        cls.set_value = opaque'),
    ('class Public(Base):', 'class Public(Base, metaclass=opaque):'),
    ('Observer(cls).names()', 'Observer(cls).names(opaque)'),
])
def test_open_class_inputs_and_effects_do_not_discharge_the_observer(tmp_path, old, new):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace(old, new))


def test_visible_method_escape_invalidates_the_observer_input(tmp_path):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE + '\nopaque(Public.set_value)\n')


def test_creation_observer_can_read_a_preserved_inherited_source_method(tmp_path):
    source = SOURCE.replace('class Base:',
        'class Ancestor:\n    def set_inherited(self, value): pass\nclass Base(Ancestor):')
    result, path = analyze(tmp_path, source)
    query = result.inputs['entry_binding']['class_creation_hooks'][0]['class_metadata_queries'][0]
    assert {member['attribute'] for member in query['input_binding']['matching_members']} == {
        'set_value', 'set_inherited'}
    assert runpy.run_path(str(path))['Public'].names == ['set_inherited', 'set_value']


@pytest.mark.parametrize('tail', [
    'Public.set_other = opaque',
    'Base.set_other = opaque',
    'opaque(Public)',
    'Observer.names = opaque',
])
def test_observer_input_does_not_hide_external_namespace_changes(tmp_path, tail):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE + '\n' + tail + '\n')


def test_duplicate_prefixed_member_definitions_are_not_a_unique_formation(tmp_path):
    source = SOURCE.replace('    def set_value(self, value): self.value = value',
        '    def set_value(self, value): pass\n    def set_value(self, value): self.value = value')
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


def test_observer_class_input_retains_budget_exhaustion_as_a_boundary(tmp_path):
    path = tmp_path / 'example.py'
    path.write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'), max_call_contexts=1,
                         max_class_effect_steps=1)


def test_creation_observer_reuses_doc_decoration_formation(tmp_path):
    source = 'def document(fn):\n    fn.__doc__ = "native documentation"\n    return fn\n' + SOURCE
    source = source.replace('    def set_value(self, value):',
                            '    @document\n    def set_value(self, value):')
    result, _ = analyze(tmp_path, source)
    members = result.inputs['entry_binding']['class_creation_hooks'][0][
        'class_metadata_queries'][0]['input_binding']['matching_members']
    assert members[0]['metadata_formation']['decorations']


def test_metadata_observer_does_not_assume_a_decorated_module_field_is_string(tmp_path):
    source = 'def document(fn):\n    fn.__module__ = None\n    return fn\n' + SOURCE
    source = source.replace('    def set_value(self, value):',
                            '    @document\n    def set_value(self, value):')
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


def test_observer_keeps_only_completed_ancestor_phase_records(tmp_path):
    source = SOURCE.replace('class Base:', '''class Ancestor:
    def __init_subclass__(cls): cls.base_marker = True
class Base(Ancestor):''')
    result, _ = analyze(tmp_path, source)
    hooks = result.inputs['entry_binding']['class_creation_hooks']
    query = hooks[-1]['class_metadata_queries'][0]
    ancestors = query['input_binding']['ancestor_creation_hooks']
    assert len(ancestors) == 1
    assert ancestors[0]['attributes'] == ['base_marker']
    assert 'class_metadata_queries' not in ancestors[0]
    json.dumps(result.to_dict())


ALIAS_DECORATOR = '''def aliases(cls):
    def create():
        def method(self, value): return value
        return method
    generated = create()
    generated.__doc__ = 'Alias for `{}`.'.format('set_value')
    setattr(cls, 'set_alias', generated)
    return cls
'''


def alias_source():
    return ALIAS_DECORATOR + SOURCE.replace('class Base:', '@aliases\nclass Base:')


def test_creation_observer_consumes_generated_ancestor_function_metadata(tmp_path):
    result, path = analyze(tmp_path, alias_source())
    query = result.inputs['entry_binding']['class_creation_hooks'][-1]['class_metadata_queries'][0]
    members = query['input_binding']['matching_members']
    generated = next(member for member in members if member['attribute'] == 'set_alias')
    assert generated['metadata_formation']['metadata_shapes']['documentation'] == ['str']
    assert generated['metadata_formation']['current_namespace_binding_confirmed'] is False
    assert query['input_binding']['ancestor_class_decorations']
    assert runpy.run_path(str(path))['Public'].names == ['set_alias', 'set_value']
    json.dumps(result.to_dict())


@pytest.mark.parametrize('extra', [
    'cls.set_alias = opaque',
    "setattr(cls, 'set_alias', opaque)",
    'generated.__doc__ = opaque',
    "cls.set_other = opaque",
])
def test_other_ancestor_writes_cannot_borrow_generated_function_evidence(tmp_path, extra):
    source = alias_source().replace("setattr(cls, 'set_alias', generated)",
        "setattr(cls, 'set_alias', generated)\n    " + extra)
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


def test_ancestor_alias_native_metadata_requires_its_source_lookup(tmp_path):
    source = alias_source().replace('def aliases(cls):', 'import functools\ndef aliases(cls):')
    source = source.replace('        def method(self, value):',
        "        @functools.wraps(getattr(cls, 'set_base'))\n        def method(self, value):")
    source = source.replace('class Base:\n', 'class Base:\n    def set_base(self, value): pass\n')
    result, path = analyze(tmp_path, source)
    query = result.inputs['entry_binding']['class_creation_hooks'][-1]['class_metadata_queries'][0]
    alias = next(member for member in query['input_binding']['matching_members']
                 if member['attribute'] == 'set_alias')
    assert alias['metadata_formation']['metadata_wrappers'][0]['wrapped_lookup'][
        'target']['qualname'] == 'Base.set_base'
    assert runpy.run_path(str(path))['Public'].names == ['set_alias', 'set_base', 'set_value']


def test_joined_function_metadata_cannot_preserve_an_earlier_alias_snapshot(tmp_path):
    source = alias_source().replace(
        "    generated.__doc__ = 'Alias for `{}`.'.format('set_value')\n    setattr(cls, 'set_alias', generated)",
        "    if unknown:\n        generated.__doc__ = 'native documentation'\n"
        "        setattr(cls, 'set_alias', generated)\n    generated.__doc__ = opaque")
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


@pytest.mark.parametrize('moment', ['before', 'after'])
def test_a_local_alias_metadata_write_invalidates_the_published_function(tmp_path, moment):
    source = alias_source().replace("setattr(cls, 'set_alias', generated)",
        "saved = generated\n    " +
        ("saved.__doc__ = opaque\n    setattr(cls, 'set_alias', generated)" if moment == 'before' else
         "setattr(cls, 'set_alias', generated)\n    saved.__doc__ = opaque"))
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


def test_signature_can_consume_a_bound_private_string_list_without_guessing_names(tmp_path):
    source = 'from inspect import Signature, Parameter\n' + SOURCE
    source = source.replace('cls.names = Observer(cls).names()', '''cls.signature = Signature([
            Parameter('self', Parameter.POSITIONAL_OR_KEYWORD),
            *[Parameter(name, Parameter.KEYWORD_ONLY, default=None)
              for name in Observer(cls).names()]])''')
    result, _ = analyze(tmp_path, source)
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    signature = hook['signature_creations'][0]
    assert signature['input_binding'] == 'source_dynamic_native_metadata'
    assert signature['dynamic_parameters'][0]['input_query'] == hook['class_metadata_queries'][0]
    assert signature['dynamic_parameters'][0]['names'] == 'unresolved_native_strings'
    assert signature['completion'] == 'normal_return_only'
    assert 'parameter_names' not in signature


@pytest.mark.parametrize('change', [
    ('Parameter(name, Parameter.KEYWORD_ONLY', 'Parameter(opaque(name), Parameter.KEYWORD_ONLY'),
    ('for name in Observer(cls).names()', 'for name in opaque(cls)'),
    ('for name in Observer(cls).names()', 'for name in Observer(cls).names() if opaque(name)'),
    ('Parameter(name, Parameter.KEYWORD_ONLY', 'Parameter(name, Parameter.POSITIONAL_OR_KEYWORD'),
])
def test_dynamic_signature_cannot_hide_callback_inputs(tmp_path, change):
    source = 'from inspect import Signature, Parameter\n' + SOURCE.replace(
        'cls.names = Observer(cls).names()', '''cls.signature = Signature([
            *[Parameter(name, Parameter.KEYWORD_ONLY, default=None)
              for name in Observer(cls).names()]])''')
    with pytest.raises(ValueError):
        analyze(tmp_path, source.replace(*change))


@pytest.mark.parametrize('replacement', ['default=name', 'default=opaque(name)'])
def test_dynamic_parameter_scope_cannot_borrow_a_module_default_binding(tmp_path, replacement):
    source = 'from inspect import Signature, Parameter\n' + SOURCE.replace(
        'cls.names = Observer(cls).names()', '''cls.signature = Signature([
            *[Parameter(name, Parameter.KEYWORD_ONLY, default=None)
              for name in Observer(cls).names()]])''')
    source = 'class Marker: pass\nname = Marker()\n' + source
    with pytest.raises(ValueError):
        analyze(tmp_path, source.replace('default=None', replacement))


def test_dynamic_signature_literal_exclusions_preserve_native_iteration(tmp_path):
    source = 'from inspect import Signature, Parameter\n' + SOURCE.replace(
        'cls.names = Observer(cls).names()', '''cls.signature = Signature([
            *[Parameter(name, Parameter.KEYWORD_ONLY, default=None)
              for name in Observer(cls).names() if name not in ['set_hidden', 'set_other']]])''')
    result, _ = analyze(tmp_path, source)
    segment = result.inputs['entry_binding']['class_creation_hooks'][0][
        'signature_creations'][0]['dynamic_parameters'][0]
    assert segment['filters'][0]['operation'] == 'native_string_not_in_literal_sequence'
    assert segment['filters'][0]['excluded_names'] == ['set_hidden', 'set_other']
    assert segment['names'] == 'unresolved_native_strings'


@pytest.mark.parametrize('exclusion', ['opaque', '[opaque]', '[name]', 'get_exclusions()'])
def test_dynamic_signature_filters_require_independent_native_data(tmp_path, exclusion):
    source = 'from inspect import Signature, Parameter\n' + SOURCE.replace(
        'cls.names = Observer(cls).names()', '''cls.signature = Signature([
            *[Parameter(name, Parameter.KEYWORD_ONLY, default=None)
              for name in Observer(cls).names() if name not in ''' + exclusion + ''']])''')
    with pytest.raises(ValueError):
        analyze(tmp_path, source)
