## @package tests.test_function_observation

import pytest

from pcresolve import FlowAnalyzer
from pcresolve.flow.proofs._function_observation import nonobserving_source


SOURCE = '''import sys
def location():
    frame = sys._getframe()
    while frame:
        module = frame.f_globals.get('__name__', '')
        line = frame.f_lineno
        code = frame.f_code
        frame = frame.f_back
    return module, line, code
def active():
    for frame in sys._current_frames().values():
        while frame:
            if frame.f_code in codes: return True
            frame = frame.f_back
    return False
'''


def inspect(root, source=SOURCE):
    (root / 'sample.py').write_text(source, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    return analyzer, nonobserving_source(analyzer)


def test_native_frame_metadata_does_not_export_a_frame_or_its_locals(tmp_path):
    analyzer, fact = inspect(tmp_path)
    assert fact is not None
    assert fact['source_hashes'] == analyzer.hashes
    assert [item['function']['qualname'] for item in fact['frame_metadata']] == ['location', 'active']
    assert all(item['scope'] == 'native_frame_metadata_only' for item in fact['frame_metadata'])
    assert 'no_external_frame_or_gc_observation' in fact['assumptions']


def test_native_frame_factory_alias_is_checked_by_its_import_binding(tmp_path):
    text = SOURCE.replace('import sys', 'import sys\nfrom sys import _getframe as frame_factory')
    text = text.replace('sys._getframe()', 'frame_factory()')
    _, fact = inspect(tmp_path, text)
    assert fact is not None
    assert fact['frame_metadata'][0]['factory'] == 'sys._getframe'


WALK_STACK = '''import traceback
def location():
    for frame, line in traceback.walk_stack(None):
        if frame is None: break
        module = frame.f_globals.get('__name__', '')
        name = frame.f_code.co_name
        if name == 'public': break
    return module, line, name
'''


def test_native_stack_iteration_can_limit_each_frame_to_metadata(tmp_path):
    _, fact = inspect(tmp_path, WALK_STACK)
    assert fact is not None
    record, = fact['frame_metadata']
    assert record['factory'] == 'traceback.walk_stack'
    assert record['fields'] == ['f_code', 'f_globals']
    assert 'standard_traceback_frame_iteration_protocol' in fact['assumptions']


@pytest.mark.parametrize('old,new', [
    ('walk_stack(None)', 'walk_stack(unknown)'),
    ('walk_stack(None)', 'walk_stack()'),
    ('walk_stack(None)', 'walk_stack(None, unknown)'),
    ('walk_stack(None)', 'walk_stack(None, flag=True)'),
    ('for frame, line in', 'for frame in'),
    ("module = frame.f_globals.get('__name__', '')", 'opaque(frame)'),
    ('return module, line, name', 'return frame'),
    ('def location():', 'def location(traceback):'),
])
def test_unproved_frame_iterators_and_frame_escape_keep_the_guard_open(tmp_path, old, new):
    _, fact = inspect(tmp_path, WALK_STACK.replace(old, new))
    assert fact is None


def test_replacing_the_native_traceback_factory_invalidates_its_metadata_model(tmp_path):
    assert inspect(tmp_path, WALK_STACK + '\ntraceback.walk_stack = opaque\n')[1] is None


@pytest.mark.parametrize('attribute', ['f_back', 'f_globals', 'f_code'])
def test_a_valid_metadata_reader_does_not_approve_an_unrooted_frame_parameter(tmp_path, attribute):
    text = SOURCE + f'\ndef unrooted(value): return value.{attribute}\n'
    assert inspect(tmp_path, text)[1] is None


@pytest.mark.parametrize('replacement', [
    'return frame', 'opaque(frame)', 'other = frame',
    'return frame.f_locals', "return frame.f_globals['target']",
    "return frame.f_globals.get('target')", 'frame.f_trace = opaque',
    'return lambda: frame.f_code', 'yield frame.f_code',
    'frame = opaque()', 'import unknown as frame',
    'try:\n            pass\n        except Exception as frame:\n            pass',
    'class Saved:\n            frame = frame.f_back',
])
def test_frames_and_local_object_capabilities_remain_boundaries(tmp_path, replacement):
    _, fact = inspect(tmp_path, SOURCE.replace("module = frame.f_globals.get('__name__', '')",
                                              replacement))
    assert fact is None


@pytest.mark.parametrize('tail', [
    'sys._getframe = opaque',
    'from sys import settrace as trace\ntrace(opaque)',
    'from sys import _getframe as factory\nopaque(factory())',
    'from gc import get_objects as objects\nobjects()',
    'saved = sys._getframe',
    'import inspect\ninspect.stack()',
    'import inspect\nsaved = inspect.stack',
    'import gc\ngc.get_objects()',
    'import gc\ngc.get_referrers(value)',
    'frame = sys._getframe()',
    "name = 'f_locals'", 'opaque.gi_frame',
    'def inspect_dynamic(): return eval(code)',
    '''def inspect_dynamic():
    return eval("__import__('sys')._getframe(1).f_locals", {'__builtins__': {}})''',
    "def mutate(): globals()['helper'] = opaque",
    'def mutate(): helper.__code__ = opaque',
    'import sample\ndef mutate(): sample.location = opaque',
])
def test_unbounded_observers_and_native_api_replacement_invalidate_isolation(tmp_path, tail):
    assert inspect(tmp_path, SOURCE + '\n' + tail + '\n')[1] is None


def test_shadowed_frame_factories_are_not_native_protocols(tmp_path):
    assert inspect(tmp_path, SOURCE.replace('def location():', 'def location(sys):'))[1] is None


def test_a_parameter_is_not_a_native_frame_before_conditional_rebinding(tmp_path):
    text = SOURCE.replace('def location():\n    frame = sys._getframe()',
        'def location(frame):\n    if flag:\n        frame = sys._getframe()')
    assert inspect(tmp_path, text)[1] is None


def test_source_edits_invalidate_the_observer_guard(tmp_path):
    analyzer, fact = inspect(tmp_path)
    assert fact is not None
    (tmp_path / 'sample.py').write_text(SOURCE + '\nimport gc\ngc.get_objects()\n', encoding='utf-8')
    analyzer._index()
    assert nonobserving_source(analyzer) is None
