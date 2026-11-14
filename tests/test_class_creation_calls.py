## @package tests.test_class_creation_calls

import runpy

import pytest


def test_written_attributes_is_available_without_creation_orchestration():
    from pcresolve.flow.proofs._class_effect_attributes import written_attributes
    assert written_attributes([{'attributes': ['a', 'b']}, {'attributes': ['a']}]) == {'a', 'b'}

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.proofs._class_creation_calls import creation_calls


SOURCE = '''def fixed(allowed=0): return allowed
class Base:
    def __init_subclass__(cls):
        cls.refresh()
    @classmethod
    def refresh(cls):
        cls.stage()
        cls.ready = True
    @classmethod
    def stage(cls):
        cls.marker = 1
class Public(Base):
    def __init__(self, **kwargs): fixed(**kwargs)
'''


def analyze(root, text=SOURCE):
    path = root / 'example.py'
    path.write_text(text, encoding='utf-8')
    return FlowAnalyzer(project_root=root).analyze(FunctionRef('example', 'Public')), path


def test_creation_hook_can_follow_a_closed_source_classmethod_graph(tmp_path):
    result, path = analyze(tmp_path)
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    assert set(hook['attributes']) == {'ready', 'marker'}
    calls = hook['method_calls']
    assert [call['target']['qualname'] for call in calls] == ['Base.refresh', 'Base.stage']
    assert all(call['binding'] == 'builtin_classmethod' for call in calls)
    assert all(call['receiver_class'] == hook['receiver_class'] for call in calls)
    assert all(call['completion'] == 'normal_return_only' for call in calls)
    assert 'source_class_creation_call_graph' in hook['assumptions']
    namespace = runpy.run_path(str(path))
    assert namespace['Public'].ready is True and namespace['Public'].marker == 1
    with pytest.raises(TypeError):
        namespace['Public'](old=1)


def test_callable_metadata_query_accepts_missing_ancestor_hook_facts(tmp_path):
    source = '''class Base:
    @classmethod
    def refresh(cls): pass
    def __init_subclass__(cls):
        if hasattr(cls.refresh, "__signature__"):
            cls.ready = True
class Child(Base): pass
'''
    path = tmp_path / 'example.py'
    path.write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    target = next((ref, node) for ref, node in analyzer.classes if ref.qualname == 'Child')
    hook = next((ref, node) for ref, node in analyzer.definitions
                 if ref.qualname == 'Base.__init_subclass__')

    # The caller may have no independently proved ancestor creation hooks.
    # The query must remain conservative instead of iterating over None.
    assert creation_calls(analyzer, target, hook) is None


def test_classmethod_dispatch_uses_the_new_subclass_mro(tmp_path):
    text = SOURCE.replace('    def __init__(self, **kwargs)',
                          '    @classmethod\n    def stage(cls): cls.subclass_marker = 2\n'
                          '    def __init__(self, **kwargs)')
    result, path = analyze(tmp_path, text)
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    assert set(hook['attributes']) == {'ready', 'subclass_marker'}
    assert hook['method_calls'][1]['target']['qualname'] == 'Public.stage'
    assert runpy.run_path(str(path))['Public'].subclass_marker == 2


@pytest.mark.parametrize('body', [
    'opaque(cls)', 'opaque()', 'cls.__init__ = opaque',
    'cls.refresh()', 'cls.marker = opaque.attribute',
    'cls.marker = opaque + 1', 'cls.marker = {opaque: 1}',
    'cls.marker = f"{opaque}"', 'cls.stage = opaque',
    'cls.marker = cls.stage()', 'cls.stage(opaque())',
    'if opaque:\n            cls.marker = 1',
    'cls.__dict__["__init__"] = opaque',
])
def test_open_callee_effects_cannot_preserve_a_constructor(tmp_path, body):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace('cls.marker = 1', body))


@pytest.mark.parametrize('replacement', [
    '    def stage(cls):',
    '    @staticmethod\n    def stage(cls):',
    '    @opaque\n    def stage(cls):',
])
def test_the_callee_needs_an_exact_builtin_classmethod_binding(tmp_path, replacement):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace('    @classmethod\n    def stage(cls):', replacement))


@pytest.mark.parametrize('prefix', [
    'cls.stage = opaque\n        ',
    "setattr(cls, 'stage', opaque)\n        ",
    'cls.refresh = opaque\n        ',
])
def test_prior_or_transitive_writes_cannot_reuse_an_old_method_binding(tmp_path, prefix):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace('cls.refresh()', prefix + 'cls.refresh()', 1))


@pytest.mark.parametrize('tail', [
    'Base.stage = opaque',
    'saved = Base.stage\nsaved.__func__.__code__ = opaque',
    'opaque(Base.stage)',
])
def test_visible_method_replacements_or_escapes_invalidate_the_graph(tmp_path, tail):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE + '\n' + tail + '\n')


def test_call_graph_budget_is_bounded(tmp_path):
    methods = '\n'.join('    @classmethod\n    def m%d(cls): cls.m%d()' % (i, i + 1)
                        for i in range(20))
    methods += '\n    @classmethod\n    def m20(cls): cls.marker = 1\n'
    text = SOURCE.replace('cls.refresh()', 'cls.m0()', 1).replace('class Public(Base):',
                           methods + '\nclass Public(Base):')
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


def test_matplotlib_set_function_name_writes_do_not_hide_other_class_effects(tmp_path):
    package = tmp_path / 'matplotlib'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    (package / 'artist.py').write_text('''class Artist:
    def __init_subclass__(cls):
        cls.set = lambda self, **kwargs: Artist.set(self, **kwargs)
        cls.set.__name__ = "set"
        cls.set.__qualname__ = f"{cls.__qualname__}.set"
    def set(self, **kwargs): return kwargs
''', encoding='utf-8')
    (package / 'patches.py').write_text('''from .artist import Artist
class Patch(Artist): pass
''', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index()
    target = analyzer._definition_index.find(
        'matplotlib.patches', 'Patch', kind='class')[0]
    hook = analyzer._definition_index.find(
        'matplotlib.artist', 'Artist.__init_subclass__')[0]
    prefix = {'kind': 'source_class_creation_prefix', 'status': 'source_bound',
              'receiver_class': {'module': 'matplotlib.patches', 'qualname': 'Patch'}}

    fact = creation_calls(analyzer, target, hook, module_prefix=prefix)

    assert fact is not None
    assert fact[0] == ['set']
    assert [query['attribute'] for query in fact[-1]] == ['__name__', '__qualname__']
    assert all(query['effect_scope'] == 'function_metadata_only' for query in fact[-1])


def test_repeated_calls_share_effects_but_keep_each_source_call_site(tmp_path):
    result, _ = analyze(tmp_path, SOURCE.replace('cls.refresh()', 'cls.refresh()\n        cls.refresh()', 1))
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    assert len(hook['method_calls']) == 3
    assert len({(call['caller']['qualname'], call['call_evidence']['lineno'])
                for call in hook['method_calls']}) == 3
    assert set(hook['attributes']) == {'ready', 'marker'}


def test_an_ancestor_hook_override_is_not_a_source_classmethod_binding(tmp_path):
    text = SOURCE.replace('class Base:', '''class Ancestor:
    def __init_subclass__(cls): cls.refresh = unknown_callable
class Base(Ancestor):''')
    with pytest.raises(ValueError):
        analyze(tmp_path, text)


@pytest.mark.parametrize('assignment', [
    'cls.callback = lambda self, **kwargs: fixed(**kwargs)',
    'callback = lambda self, **kwargs: fixed(**kwargs)\n        cls.callback = callback',
    'cls.callback = lambda self, value=1, *, enabled=True: opaque(value, enabled)',
])
def test_creating_a_callback_does_not_execute_its_body(tmp_path, assignment):
    result, path = analyze(tmp_path, SOURCE.replace('cls.marker = 1', assignment))
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    assert set(hook['attributes']) == {'ready', 'callback'}
    assert [call['target']['qualname'] for call in hook['method_calls']] == ['Base.refresh', 'Base.stage']
    # The unrelated constructor still rejects the original extra keyword. The
    # callback's body is not needed to construct the class or this instance.
    with pytest.raises(TypeError):
        runpy.run_path(str(path))['Public'](old=1)


def test_a_hook_can_store_a_deferred_global_method_lookup(tmp_path):
    source = SOURCE.replace('cls.refresh()',
        'cls.callback = lambda self, **kwargs: Base.forward(self, **kwargs)\n        cls.refresh()', 1)
    source = source.replace('class Public(Base):',
                            '    def forward(self, **kwargs): return fixed(**kwargs)\nclass Public(Base):')
    result, path = analyze(tmp_path, source)
    hook = result.inputs['entry_binding']['class_creation_hooks'][0]
    assert set(hook['attributes']) == {'callback', 'ready', 'marker'}
    assert runpy.run_path(str(path))['Public']().callback(allowed=4) == 4


@pytest.mark.parametrize('assignment', [
    'cls.callback = (lambda: opaque())()',
    'callback = lambda: opaque()\n        callback()',
    'cls.callback = lambda value=opaque(): value',
    'cls.callback = lambda *, value=opaque(): value',
    'cls.callback = lambda value=cls: value',
    'cls.callback = lambda: opaque(cls)',
    'held = cls\n        cls.callback = lambda: opaque(held)',
    'callback = lambda: opaque(held)\n        held = cls\n        cls.callback = callback',
    'cls.callback = lambda: opaque(held)\n        held = cls',
    'cls.__init__ = lambda self, **kwargs: None',
    'cls.callback = lambda: setattr(cls, "__init__", opaque)',
    'cls.callback = lambda: cls.stage()',
])
def test_deferred_syntax_cannot_hide_immediate_calls_or_retained_class_cells(tmp_path, assignment):
    with pytest.raises(ValueError):
        analyze(tmp_path, SOURCE.replace('cls.marker = 1', assignment))


def test_a_callback_default_can_change_the_constructor_during_class_creation(tmp_path):
    source = SOURCE.replace('cls.marker = 1',
                            'cls.callback = lambda value=replace(cls): value')
    source = source.replace('class Base:', '''def replace(cls):
    cls.__init__ = lambda self, **kwargs: None
class Base:''')
    with pytest.raises(ValueError):
        analyze(tmp_path, source)
    assert runpy.run_path(str(tmp_path / 'example.py'))['Public'](old=1) is not None


def test_late_bound_callback_cells_are_not_discarded_as_global_lookups(tmp_path):
    source = SOURCE.replace('cls.marker = 1', '''cls.callback = lambda: replace(held)
        held = cls''')
    source = source.replace('class Base:', '''def replace(cls):
    cls.__init__ = lambda self, **kwargs: None
class Base:''')
    with pytest.raises(ValueError):
        analyze(tmp_path, source)
    cls = runpy.run_path(str(tmp_path / 'example.py'))['Public']
    cls.callback()
    assert cls(old=1) is not None
