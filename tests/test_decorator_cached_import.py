## @package tests.test_decorator_cached_import

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def setup(root, prefix='import dependency\n', export=None, extra=''):
    (root / 'dependency.py').write_text(export or '''class Holder:
    def update(self): self.value = True
def text(value): return value
''', encoding='utf-8')
    (root / 'decorators.py').write_text('''class Document:
    def __call__(self, fn):
        from dependency import text as render
        fn.__doc__ = render('documentation')
        return fn
''', encoding='utf-8')
    (root / 'entry.py').write_text(prefix + '''from decorators import Document
def fixed(allowed=0): return allowed
@Document()
def entry(**kwargs): return fixed(**kwargs)
''' + extra, encoding='utf-8')
    result = FlowAnalyzer(project_root=root).analyze(FunctionRef('entry', 'entry'))
    return result.functions[0]['decorator_effects'][0]


def test_entry_initialization_can_support_a_later_import_inside_a_decorator(tmp_path):
    fact = setup(tmp_path)
    assert fact['body_binding_status'] == 'preserved'
    assert not fact['boundaries']
    imported = next(effect for effect in fact['effects'] if effect['operation'] == 'cached_import')
    proof = imported['binding']
    assert proof['status'] == 'bound_on_normal_cached_import_return'
    assert proof['initialization_function']['module'] == 'entry'
    assert proof['bindings'] == [{'name': 'render', 'module': 'dependency', 'attribute': 'text'}]
    assert ({str(tmp_path / name) for name in ('entry.py', 'decorators.py', 'dependency.py')}
            <= set(proof['source_hashes']))
    assert proof['runtime_import_confirmed'] is False


@pytest.mark.parametrize('prefix,export,extra', [
    ('', None, ''),
    ('if flag:\n    import dependency\n', None, ''),
    ('import dependency\ndependency = unknown\n', None, ''),
    ('import dependency\ndependency.text = unknown\n', None, ''),
    ('import dependency\nimport sys\nsys.modules.clear()\n', None, ''),
    ('import dependency\nimport sys\ndel sys.modules["dependency"]\n', None, ''),
    ('import dependency\n', 'def __getattr__(name): return unknown\ndef text(value): return value\n', ''),
    ('import dependency\n', 'def text(value): return value\ndef alter():\n global text\n text = unknown\n', ''),
    ('import dependency\n', 'text = unknown\n', ''),
    ('import dependency\n', None, '\nsetattr(dependency, "text", unknown)\n'),
    ('import dependency\n', None, '\nopaque(dependency)\n'),
    ('import dependency\n', None, '\nnamespace = dependency.__dict__\n'),
    ('import dependency\n', None, '\nimport builtins\nbuiltins.__import__ = unknown\n'),
    ('import dependency\n', None,
     '\ndef alter():\n dependency.text.__globals__["text"] = unknown\n'),
    ('import dependency\n', None, '\ndef alter():\n dependency.text.__code__ = unknown\n'),
    ('import dependency\n', None,
     '\nrenderer = dependency.text\nrenderer.__code__ = unknown\n'),
    ('import dependency\n', None, '\nopaque(dependency.text)\n'),
    ('import dependency\n', None,
     '\nfrom dependency import text as renderer\nopaque(renderer)\n'),
])
def test_unconfirmed_cache_export_or_module_binding_keeps_the_boundary(tmp_path, prefix, export, extra):
    fact = setup(tmp_path, prefix, export, extra)
    assert fact['body_binding_status'] != 'preserved'
    assert fact['boundaries']


def test_relative_package_initialization_keeps_the_exact_loaded_submodule(tmp_path):
    package = tmp_path / 'bundle'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / 'data.py').write_text('def render(text): return text\n', encoding='utf-8')
    (package / 'docs.py').write_text('''class Document:
    def __call__(self, fn):
        from bundle.data import render
        fn.__doc__ = render('text')
        return fn
''', encoding='utf-8')
    (package / 'entry.py').write_text('''from . import data
from .docs import Document
@Document()
def entry(**kwargs): return kwargs
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('bundle.entry', 'entry'))
    fact = result.functions[0]['decorator_effects'][0]
    assert fact['body_binding_status'] == 'preserved'
    imported = next(effect['binding'] for effect in fact['effects'] if effect['operation'] == 'cached_import')
    assert imported['bindings'][0]['module'] == 'bundle.data'
    assert imported['initialization_evidence'][0]['lineno'] == 1


def test_cached_import_proof_has_an_independent_runtime_control(tmp_path, monkeypatch):
    setup(tmp_path)
    monkeypatch.syspath_prepend(str(tmp_path))
    values = runpy.run_path(str(tmp_path / 'entry.py'))
    assert values['entry'].__doc__ == 'documentation'
    values['entry'](allowed=1)
    with pytest.raises(TypeError, match="unexpected keyword argument 'old'"):
        values['entry'](old=1)


def test_namespace_cache_is_rebuilt_when_source_changes(tmp_path):
    setup(tmp_path)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    first = analyzer.analyze(FunctionRef('entry', 'entry'))
    snapshot = first.to_dict()
    with (tmp_path / 'dependency.py').open('a', encoding='utf-8') as stream:
        stream.write('\ndef replace():\n global text\n text = unknown\n')
    changed = analyzer.analyze(FunctionRef('entry', 'entry'))
    assert changed.functions[0]['decorator_effects'][0]['body_binding_status'] == 'unknown'
    assert first.to_dict() == snapshot


def test_namespace_budget_cannot_reuse_a_previous_complete_proof(tmp_path, monkeypatch):
    from pcresolve.flow.proofs import _decorator_imports

    setup(tmp_path)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    first = analyzer.analyze(FunctionRef('entry', 'entry'))
    saved = first.to_dict()
    with monkeypatch.context() as patch:
        patch.setattr(_decorator_imports, '_DECORATOR_IMPORT_NODE_LIMIT', 1)
        result = analyzer.analyze(FunctionRef('entry', 'entry'))
        fact = result.functions[0]['decorator_effects'][0]
        assert fact['body_binding_status'] == 'unknown'
        assert any(boundary['reason'] == 'decorator_cached_import_unproven'
                   for boundary in fact['boundaries'])
    assert analyzer.analyze(FunctionRef('entry', 'entry')).to_dict() == saved
    assert first.to_dict() == saved


@pytest.mark.parametrize('package_source', [
    'data = object()\n',
    'def __getattr__(name): return object()\n',
    'class Changes:\n def change(self):\n  global data\n  data = object()\n',
    "__path__ = ['other']\n",
    '__class__ = unknown\n',
])
def test_package_attribute_or_custom_lookup_does_not_prove_submodule_initialization(tmp_path, package_source):
    package = tmp_path / 'bundle'
    package.mkdir()
    (package / '__init__.py').write_text(package_source, encoding='utf-8')
    (package / 'data.py').write_text('def render(text): return text\n', encoding='utf-8')
    (tmp_path / 'docs.py').write_text('''class Document:
    def __call__(self, fn):
        from bundle.data import render
        fn.__doc__ = render('text')
        return fn
''', encoding='utf-8')
    (tmp_path / 'entry.py').write_text('''from bundle import data
from docs import Document
@Document()
def entry(**kwargs): return kwargs
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'entry'))
    assert result.functions[0]['decorator_effects'][0]['body_binding_status'] == 'unknown'


@pytest.mark.parametrize('extra', [
    "\nimport bundle\ndef alter(): bundle.data = unknown\n",
    "\nimport bundle\nopaque(bundle)\n",
    "\ndef alter(): globals()['data'] = unknown\n",
])
def test_package_namespace_writes_and_escapes_cannot_supply_a_submodule_premise(tmp_path, extra):
    package = tmp_path / 'bundle'
    package.mkdir()
    (package / '__init__.py').write_text(extra, encoding='utf-8')
    (package / 'data.py').write_text('def render(text): return text\n', encoding='utf-8')
    (tmp_path / 'docs.py').write_text('''class Document:
    def __call__(self, fn):
        from bundle.data import render
        fn.__doc__ = render('text')
        return fn
''', encoding='utf-8')
    (tmp_path / 'entry.py').write_text('''from bundle import data
from docs import Document
@Document()
def entry(**kwargs): return kwargs
''', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('entry', 'entry'))
    assert result.functions[0]['decorator_effects'][0]['body_binding_status'] == 'unknown'
