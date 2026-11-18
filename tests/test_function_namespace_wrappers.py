## @package tests.test_function_namespace_wrappers

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.proofs._class_definition import namespace_issues
from pcresolve.flow.proofs._function_namespace import wrapper_creation


SOURCE = '''from functools import wraps
def decorate(fn):
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        # This body is deferred during class namespace formation.
        return opaque(fn, self, args, kwargs)
    wrapper.flag = False
    return wrapper
def fixed(allowed=0): return allowed
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
    @decorate
    def unrelated(self): return 'original'
'''


def prepare(root, text=SOURCE):
    path = root / 'example.py'
    path.write_text(text, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    member = analyzer._definition_index.find('example', 'Public.unrelated')[0]
    return analyzer, member, path


def test_wrapper_creation_proves_namespace_kind_without_proving_original_body(tmp_path):
    analyzer, target, path = prepare(tmp_path)
    fact = wrapper_creation(analyzer, target)
    assert fact['result_kind'] == 'native_function'
    assert fact['body_binding_status'] == 'unmodeled'
    assert fact['identity_status'] == 'replaced'
    assert fact['future_body_effects'] == 'unmodeled'
    assert fact['runtime_decorator_executed'] is False
    hierarchy = analyzer._class_mro('example', 'Public')
    assumptions, dependencies = set(), set()
    assert not namespace_issues(analyzer, hierarchy, assumptions=assumptions,
                                dependencies=dependencies)
    assert 'source_native_function_wrapper_creation' in assumptions
    assert str(path) in dependencies
    result = analyzer.analyze(FunctionRef('example', 'Public'))
    assert result.inputs['entry_binding']['status'] == 'source_bound'
    method = analyzer.analyze(FunctionRef('example', 'Public.unrelated'))
    assert any(item['reason'] == 'decorator_effect_unconfirmed'
               for item in method.boundaries)
    namespace = runpy.run_path(str(path))
    with pytest.raises(TypeError):
        namespace['Public'](old=1)
    with pytest.raises(NameError):
        namespace['Public']().unrelated()


@pytest.mark.parametrize('old,new', [
    ('wrapper.flag = False', 'opaque()'),
    ('wrapper.flag = False', 'opaque(fn)'),
    ('wrapper.flag = False', 'opaque(wrapper)'),
    ('wrapper.flag = False', 'wrapper.__code__ = opaque'),
    ('wrapper.flag = False', 'wrapper.__dict__ = opaque'),
    ('wrapper.flag = False', 'fn.flag = False'),
    ('wrapper.flag = False', 'wrapper.flag = opaque()'),
    ('wrapper.flag = False', 'wrapper.flag = opaque.attribute'),
    ('return wrapper', 'return opaque'),
    ('return wrapper', 'return fn'),
    ('@wraps(fn)', '@wraps(opaque)'),
    ('@wraps(fn)', '@wraps(fn, updated=())'),
    ('@wraps(fn)', '@opaque'),
    ('def wrapper(self, *args, **kwargs):', 'def wrapper(self, value=opaque()):'),
    ('def wrapper(self, *args, **kwargs):', 'def wrapper(self: opaque()):'),
    ('def decorate(fn):', 'def decorate(fn):\n    global wrapper'),
    ('def decorate(fn):', '@opaque\ndef decorate(fn):'),
    ('def decorate(fn):', 'def decorate(fn, another):'),
    ('@decorate\n    def unrelated', '@decorate\n    @opaque\n    def unrelated'),
])
def test_open_immediate_effects_do_not_acquire_a_function_namespace_proof(tmp_path, old, new):
    analyzer, target, _ = prepare(tmp_path, SOURCE.replace(old, new))
    assert wrapper_creation(analyzer, target) is None
    assert namespace_issues(analyzer, analyzer._class_mro('example', 'Public'),
                            assumptions=set())


def test_runtime_replacement_of_decorator_blocks_namespace_proof(tmp_path):
    text = SOURCE + "\ndef mutate():\n    globals()['decorate'] = opaque\n"
    analyzer, target, _ = prepare(tmp_path, text)
    assert wrapper_creation(analyzer, target) is None


@pytest.mark.parametrize('tail', [
    'decorate.__code__ = opaque',
    "setattr(decorate, '__defaults__', opaque)",
    'saved = decorate\nsaved.__code__ = opaque',
])
def test_visible_execution_slot_mutation_does_not_reuse_the_source_decorator(tmp_path, tail):
    analyzer, target, _ = prepare(tmp_path, SOURCE + '\n' + tail + '\n')
    assert wrapper_creation(analyzer, target) is None


def test_wrapper_body_can_define_its_own_globals_without_executing_them(tmp_path):
    text = SOURCE.replace('return opaque(fn, self, args, kwargs)',
                          'global value\n        value = opaque(fn)\n        return value')
    analyzer, target, _ = prepare(tmp_path, text)
    assert wrapper_creation(analyzer, target)['result_kind'] == 'native_function'


def test_a_wrapper_on_the_selected_constructor_does_not_authorize_its_old_body(tmp_path):
    text = SOURCE.replace('    def __init__', '    @decorate\n    def __init__')
    analyzer, _, _ = prepare(tmp_path, text)
    result = analyzer.analyze(FunctionRef('example', 'Public'))
    assert result.inputs['entry_binding']['status'] == 'unconfirmed'
    assert {'reason': 'constructor_initialization_unconfirmed'} in result.inputs[
        'entry_binding']['issues']
