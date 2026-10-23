## @package tests.test_class_deferred_helpers

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

SOURCE = '''def decorate(cls):
    def create(name):
        def method(self, value):
            return cls, name, value
        return method
    generated = create('label')
    generated.__name__ = 'alias'
    generated.__doc__ = 'Alias documentation'
    setattr(cls, 'alias', generated)
    return cls
def fixed(allowed=0): return allowed
@decorate
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
'''


def analyze(root, text=SOURCE):
    path = root / 'example.py'
    path.write_text(text, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    return analyzer.analyze(FunctionRef('example', 'Public')), path


def test_deferred_helper_returns_do_not_replace_the_outer_class(tmp_path):
    result, path = analyze(tmp_path)
    fact = result.inputs['entry_binding']['class_decorations'][0]
    assert fact['attributes'] == ['alias']
    assert fact['identity_status'] == 'preserved'
    assert fact['deferred_functions']['runtime_bodies_executed'] is False
    assert fact['deferred_functions']['scope'] == 'class_decoration_only'
    values = runpy.run_path(str(path))
    instance = values['Public'](allowed=1)
    assert instance.alias(7) == (values['Public'], 'label', 7)
    with pytest.raises(TypeError):
        values['Public'](old=1)


def test_an_unused_helper_body_can_have_its_own_receiver_name_and_return(tmp_path):
    text = SOURCE.replace('    generated = create', '''    def unused(cls):
        cls.__init__ = opaque
        return None
    generated = create''')
    result, _ = analyze(tmp_path, text)
    assert result.inputs['entry_binding']['status'] == 'source_bound'


@pytest.mark.parametrize('old,new', [
    ("generated = create('label')", "generated = opaque(cls)"),
    ('return method', 'opaque(cls)\n        return method'),
    ('return method', 'return cls'),
    ('def method(self, value):', '@opaque\n        def method(self, value):'),
    ('def method(self, value):', 'def method(self, value=opaque(cls)):'),
    ('def method(self, value):', 'def method(self, value: opaque(cls)):'),
    ('def create(name):', 'def create(name=opaque(cls)):'),
    ("generated.__name__ = 'alias'", 'opaque(generated)'),
    ("generated.__name__ = 'alias'", 'other.method = generated'),
    ("generated.__name__ = 'alias'", 'generated.__code__ = opaque'),
    ("generated.__name__ = 'alias'", 'saved = generated.__closure__'),
    ("setattr(cls, 'alias', generated)", "setattr(cls, '__init__', generated)"),
    ('return cls\ndef fixed', 'return generated\ndef fixed'),
])
def test_executed_callbacks_escaping_closures_and_constructor_writes_are_unproved(tmp_path, old, new):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace(old, new))


def test_conditional_factory_binding_is_not_a_definite_fresh_function(tmp_path):
    text = SOURCE.replace("generated = create('label')", '''if unknown:
        generated = create('label')
    else:
        generated = opaque''')
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


def test_a_nested_return_cannot_hide_an_outer_early_replacement(tmp_path):
    text = SOURCE.replace("generated = create('label')", '''if unknown:
        return opaque
    generated = create('label')''')
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


@pytest.mark.parametrize('use', ['cls.alias()', "getattr(cls, 'alias')()", 'saved = cls.alias\n    saved()'])
def test_a_stored_closure_is_not_a_harmless_literal_on_later_class_reads(tmp_path, use):
    text = SOURCE.replace('def method(self, value):\n            return cls, name, value',
                          'def method():\n            cls.__init__ = lambda self, **kwargs: None')
    text = text.replace("setattr(cls, 'alias', generated)",
                        "setattr(cls, 'alias', generated)\n    " + use)
    with pytest.raises(ValueError):
        analyze(tmp_path, text)
    # Independent execution confirms the deferred closure is now invoked and
    # replaces the constructor; accepting the original body would be unsound.
    namespace = runpy.run_path(str(tmp_path / 'example.py'))
    namespace['Public'](old=1)


def test_generated_alias_store_retains_native_function_metadata(tmp_path):
    result, _ = analyze(tmp_path)
    deferred = result.inputs['entry_binding']['class_decorations'][0]['deferred_functions']
    member = deferred['generated_class_members'][0]
    assert member['attribute'] == 'alias'
    formation = member['metadata_formation']
    assert formation['result_kind'] == 'native_python_function'
    assert formation['metadata_shapes']['documentation'] == ['str']
    assert formation['metadata_shapes']['name'] == ['str']
    assert formation['current_namespace_binding_confirmed'] is False
    assert formation['future_method_effects'] == 'unmodeled'


@pytest.mark.parametrize('value', ['opaque', 'None', '123'])
def test_generated_alias_opaque_documentation_does_not_gain_native_metadata(tmp_path, value):
    source = SOURCE.replace("'Alias documentation'", value)
    result, _ = analyze(tmp_path, source)
    deferred = result.inputs['entry_binding']['class_decorations'][0]['deferred_functions']
    members = deferred.get('generated_class_members', [])
    if members:
        assert members[0]['metadata_formation']['metadata_shapes']['documentation'] == ['NoneType']
        assert value == 'None'


def test_expression_only_private_helpers_are_validated_at_their_call_sites(tmp_path):
    source = SOURCE.replace("    generated = create('label')", '''    def keys(table):
        return {*table, *(alias for aliases in table.values() for alias in aliases)}
    overlap = keys({'value': ['alias']}) & keys({'other': ['second']})
    generated = create('label')''')
    result, _ = analyze(tmp_path, source)
    proof = result.inputs['entry_binding']['class_decorations'][0]['deferred_functions']
    assert len(proof['expression_helper_calls']) == 2
    assert all(call['effects'] == 'source_body_requires_validation'
               for call in proof['expression_helper_calls'])


@pytest.mark.parametrize('body', [
    'cls',
    'opaque(cls)',
    "setattr(cls, '__init__', opaque)",
    'keys(table)',
])
def test_expression_helper_inlining_does_not_hide_class_exposure_or_recursion(tmp_path, body):
    source = SOURCE.replace("    generated = create('label')", '''    def keys(table):
        return ''' + body + '''
    overlap = keys({'value': ['alias']}) & keys({'other': ['second']})
    generated = create('label')''')
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


def test_native_exception_branches_do_not_require_a_normal_return(tmp_path):
    source = SOURCE.replace("    generated = create('label')", '''    if unknown:
        raise ValueError('unsupported input')
    generated = create('label')''')
    result, _ = analyze(tmp_path, source)
    deferred = result.inputs['entry_binding']['class_decorations'][0]['deferred_functions']
    assert deferred['native_exception_branches'][0]['exception'] == 'ValueError'
    assert result.inputs['entry_binding']['class_decorations'][0]['completion'] == 'normal_return_only'


@pytest.mark.parametrize('exception', ['opaque(cls)', 'ValueError(cls)', 'opaque()'])
def test_exception_branches_cannot_hide_class_capabilities_or_unknown_construction(tmp_path, exception):
    source = SOURCE.replace("    generated = create('label')",
        '    if unknown:\n        raise ' + exception + "\n    generated = create('label')")
    with pytest.raises(ValueError):
        analyze(tmp_path, source)


def test_native_exception_guard_rejects_a_visible_builtin_replacement(tmp_path):
    source = 'import builtins\nbuiltins.ValueError = opaque\n' + SOURCE
    source = source.replace("    generated = create('label')",
        "    if unknown:\n        raise ValueError('unsupported')\n    generated = create('label')")
    with pytest.raises(ValueError):
        analyze(tmp_path, source)
