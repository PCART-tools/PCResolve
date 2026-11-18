## @package tests.test_class_function_metadata

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

SOURCE = '''import functools
def decorate(cls):
    def original(value): return value
    def create():
        @functools.wraps(original)
        def method(self, value): return original(value)
        return method
    generated = create()
    generated.__name__ = 'alias'
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
    return FlowAnalyzer(project_root=root).analyze(FunctionRef('example', 'Public')), path


def test_default_wraps_on_a_fresh_source_function_preserves_class_slots(tmp_path):
    result, path = analyze(tmp_path)
    fact = result.inputs['entry_binding']['class_decorations'][0]
    wrapper = fact['deferred_functions']['factory_invocations'][0]['metadata_wrappers'][0]
    assert wrapper['kind'] == 'standard_fresh_function_metadata_wrapper'
    assert wrapper['completion'] == 'normal_return_only'
    assert wrapper['wrapped_kind'] == 'fresh_source_function'
    namespace = runpy.run_path(str(path))
    assert namespace['Public'](allowed=1).alias(7) == 7
    with pytest.raises(TypeError):
        namespace['Public'](old=1)


@pytest.mark.parametrize('old,new', [
    ('functools.wraps(original)', 'functools.wraps(opaque)'),
    ('functools.wraps(original)', 'functools.wraps(original, updated=opaque)'),
    ('functools.wraps(original)', "functools.wraps(getattr(cls, 'target'))"),
    ('functools.wraps(original)', 'opaque(original)'),
    ("generated.__name__ = 'alias'", 'generated.__dict__ = opaque'),
    ('def create():', 'def create():\n        functools = opaque'),
    ('def create():', 'def create():\n        original = opaque'),
    ('def method(self, value):', 'def method(self, value=opaque(cls)):'),
])
def test_unknown_inputs_and_evaluated_function_effects_stay_unproved(tmp_path, old, new):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace(old, new))


@pytest.mark.parametrize('statement', [
    'functools.wraps = opaque',
    'functools.update_wrapper = opaque',
    'functools.partial = opaque',
    "functools.WRAPPER_ASSIGNMENTS = ('__init__',)",
    "functools.WRAPPER_UPDATES = ('__init__',)",
    'saved = functools.wraps',
    'opaque(functools)',
    "setattr(functools, 'wraps', opaque)",
    "__import__('functools').wraps = opaque",
    "import builtins\nbuiltins.getattr = opaque",
    "import builtins\nbuiltins.setattr = opaque",
    "import builtins\nbuiltins.object = opaque",
    "import builtins\nbuiltins.type = opaque",
])
def test_wraps_requires_the_complete_standard_metadata_namespace(tmp_path, statement):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace('def decorate(cls):', statement + '\ndef decorate(cls):'))


def test_an_unparsed_snapshot_file_cannot_prove_the_metadata_namespace(tmp_path):
    (tmp_path / 'broken.py').write_text('import functools\nfunctools.wraps =\n', encoding='utf-8')
    with pytest.raises(ValueError):
        analyze(tmp_path)
