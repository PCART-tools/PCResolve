## @package tests.test_class_function_reads

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

SOURCE = '''import functools
def decorate(cls):
    def create(name):
        @functools.wraps(getattr(cls, name))
        def method(self, *args, **kwargs):
            return getattr(self, name)(*args, **kwargs)
        return method
    prefix = 'set_'
    generated = create(prefix + 'value')
    generated.__name__ = 'set_alias'
    setattr(cls, 'set_alias', generated)
    return cls
def fixed(allowed=0): return allowed
@decorate
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
    def set_value(self, value): self.value = value
'''


def analyze(root, text=SOURCE):
    path = root / 'example.py'
    path.write_text(text, encoding='utf-8')
    return FlowAnalyzer(project_root=root).analyze(FunctionRef('example', 'Public')), path


def test_default_wraps_can_read_one_unchanged_source_plain_function(tmp_path):
    result, path = analyze(tmp_path)
    fact = result.inputs['entry_binding']['class_decorations'][0]
    wrapper = fact['deferred_functions']['factory_invocations'][0]['metadata_wrappers'][0]
    assert wrapper['wrapped_kind'] == 'source_plain_class_function'
    lookup = wrapper['wrapped_lookup']
    assert lookup['attribute'] == 'set_value'
    assert lookup['completion'] == 'normal_read_only'
    assert lookup['target']['qualname'] == 'Public.set_value'
    namespace = runpy.run_path(str(path))
    instance = namespace['Public'](allowed=1)
    instance.set_alias(7)
    assert instance.value == 7
    with pytest.raises(TypeError):
        namespace['Public'](old=1)


@pytest.mark.parametrize('prefix', [
    'cls.set_value = opaque',
    "setattr(cls, 'set_value', opaque)",
    "setattr(cls, unknown, opaque)",
    'other = cls\n    other.set_value = opaque',
    "getattr(cls, 'set_value').__dict__.update(opaque)",
    'if unknown:\n        cls.set_value = opaque',
])
def test_a_prior_class_or_function_mutation_cannot_reuse_the_declaration(tmp_path, prefix):
    text = SOURCE.replace("prefix = 'set_'", prefix + "\n    prefix = 'set_'")
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


@pytest.mark.parametrize('old,new', [
    ("create(prefix + 'value')", 'create(unknown)'),
    ("create(prefix + 'value')", "create('missing')"),
    ('def create(name):', 'def create(name):\n        cls = opaque'),
    ('def create(name):', 'def create(name):\n        getattr = opaque'),
    ('def set_value(self, value):', '@opaque\n    def set_value(self, value):'),
    ('def set_value(self, value): self.value = value', 'set_value = opaque'),
    ('class Public:', 'class Public(metaclass=opaque):'),
    ('class Public:', 'class Public(unknown):'),
])
def test_unknown_literal_lookup_and_class_protocols_remain_open(tmp_path, old, new):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace(old, new))


@pytest.mark.parametrize('tail', [
    'opaque(Public.set_value)',
    'saved = Public.set_value\nsaved.__dict__ = opaque',
    'Public.set_value.__dict__ = opaque',
    'saved = Public.set_value\nsaved.__dict__.update(opaque)',
])
def test_saved_or_escaped_source_function_metadata_is_not_fresh(tmp_path, tail):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE + '\n' + tail + '\n')


def test_a_base_creation_hook_is_a_real_prior_mutation_boundary(tmp_path):
    text = SOURCE.replace('@decorate\nclass Public:', '''class Base:
    def __init_subclass__(cls):
        cls.set_value = lambda self, value: None
@decorate
class Public(Base):''')
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


def test_a_later_store_to_an_unrelated_class_slot_keeps_the_read(tmp_path):
    result, _ = analyze(tmp_path, SOURCE.replace("prefix = 'set_'", "cls.marker = True\n    prefix = 'set_'"))
    assert result.inputs['entry_binding']['status'] == 'source_bound'


def test_a_rebound_class_alias_cannot_turn_an_opaque_getattr_into_a_class_read(tmp_path):
    text = SOURCE.replace('getattr(cls, name)', 'getattr(other, name)')
    text = text.replace("prefix = 'set_'", "other = cls\n    other = opaque\n    prefix = 'set_'")
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


def test_a_hook_writing_an_unrelated_slot_can_preserve_a_plain_method_read(tmp_path):
    text = SOURCE.replace('@decorate\nclass Public:', '''class Base:
    def __init_subclass__(cls): cls.marker = True
@decorate
class Public(Base):''')
    result, _ = analyze(tmp_path, text)
    binding = result.inputs['entry_binding']
    assert binding['class_creation_hooks'][0]['attributes'] == ['marker']
    lookup = binding['class_decorations'][0]['deferred_functions']['factory_invocations'][0][
        'metadata_wrappers'][0]['wrapped_lookup']
    assert lookup['target']['qualname'] == 'Public.set_value'
    assert lookup['class_creation_hooks'][0]['attributes'] == ['marker']


def test_alias_wraps_reads_a_doc_decorated_native_function(tmp_path):
    text = SOURCE.replace('def fixed(allowed=0):', '''def document(fn):
    fn.__doc__ = "updated documentation"
    return fn

def fixed(allowed=0):''').replace('    def set_value(self, value):',
                                '    @document\n    def set_value(self, value):')
    result, path = analyze(tmp_path, text)
    lookup = result.inputs['entry_binding']['class_decorations'][0][
        'deferred_functions']['factory_invocations'][0]['metadata_wrappers'][0]['wrapped_lookup']
    formation = lookup['metadata_formation']
    assert formation['result_kind'] == 'native_python_function'
    assert formation['current_namespace_binding_confirmed'] is False
    assert lookup['method_namespace'] == 'no_visible_writes_or_escapes'
    assert lookup['target']['qualname'] == 'Public.set_value'
    instance = runpy.run_path(str(path))['Public']()
    instance.set_alias(9)
    assert instance.value == 9


@pytest.mark.parametrize('effect', [
    'fn.__doc__ = opaque',
    'fn.__code__ = opaque',
    'expose(fn)',
])
def test_alias_wraps_cannot_read_an_open_decorated_function(tmp_path, effect):
    text = SOURCE.replace('def fixed(allowed=0):',
        'def document(fn):\n    ' + effect + '\n    return fn\n\ndef fixed(allowed=0):')
    text = text.replace('    def set_value(self, value):',
                        '    @document\n    def set_value(self, value):')
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


def test_decorated_function_formation_does_not_override_a_later_metadata_escape(tmp_path):
    text = SOURCE.replace('def fixed(allowed=0):', '''def document(fn):
    fn.__doc__ = "updated documentation"
    return fn

def fixed(allowed=0):''').replace('    def set_value(self, value):',
                                '    @document\n    def set_value(self, value):')
    text += '\nopaque(Public.set_value)\n'
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


NAMESPACE_SOURCE = SOURCE.replace("    prefix = 'set_'", """    if 'set_value' in vars(cls):
        cls.present = True
    inherited = getattr(cls, '_alias_map', {})
    cls._alias_map = {**inherited, 'value': ['alias']}
    prefix = 'set_'""")


def test_native_class_membership_and_absent_literal_fallback_are_separate_queries(tmp_path):
    result, _ = analyze(tmp_path, NAMESPACE_SOURCE)
    deferred = result.inputs['entry_binding']['class_decorations'][0]['deferred_functions']
    operations = {fact['operation'] for fact in deferred['class_namespace_queries']}
    assert operations == {'native_string_key_membership', 'absent_attribute_fallback'}
    assert all(fact['runtime_lookup_confirmed'] is False for fact in deferred['class_namespace_queries'])


@pytest.mark.parametrize('old,new', [
    ("'set_value' in vars(cls)", 'opaque in vars(cls)'),
    ("'set_value' in vars(cls)", "'set_value' in opaque(cls)"),
    ("getattr(cls, '_alias_map', {})", "getattr(cls, '_alias_map', opaque())"),
    ("inherited = getattr", "cls._alias_map = opaque\n    inherited = getattr"),
    ('def decorate(cls):', 'def decorate(cls):\n    vars = opaque'),
    ('def decorate(cls):', 'def decorate(cls):\n    getattr = opaque'),
])
def test_native_namespace_queries_do_not_hide_unknown_operands_and_mutations(tmp_path, old, new):
    with pytest.raises(ValueError):
        analyze(tmp_path, NAMESPACE_SOURCE.replace(old, new))


def test_class_dictionary_itself_does_not_gain_a_non_escaping_projection(tmp_path):
    source = NAMESPACE_SOURCE.replace("if 'set_value' in vars(cls):", 'if opaque(vars(cls)):')
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


def test_private_helper_parameter_shadowing_cannot_acquire_a_native_namespace_projection(tmp_path):
    source = SOURCE.replace("    prefix = 'set_'", '''    def inspect_namespace(vars):
        return 'set_value' in vars(cls)
    cls.present = inspect_namespace(opaque)
    prefix = 'set_' ''')
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


@pytest.mark.parametrize('name', ['vars', 'getattr'])
def test_visible_builtin_namespace_writes_invalidate_native_class_queries(tmp_path, name):
    source = 'import builtins\nbuiltins.' + name + ' = opaque\n' + NAMESPACE_SOURCE
    with pytest.raises(ValueError):
        analyze(tmp_path, source)
