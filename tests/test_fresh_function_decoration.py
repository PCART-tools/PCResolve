## @package tests.test_fresh_function_decoration

import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = '''def fixed(allowed=0): return allowed
class Cache(dict):
    def __missing__(self, key): return str(key)
class Documentation:
    def __init__(self): self.values = Cache()
    def __call__(self, fn):
        if fn.__doc__:
            fn.__doc__ = fn.__doc__ % self.values
        return fn
document = Documentation()
@document
def public(**kwargs):
    """%(description)s"""
    return fixed(**kwargs)
'''


def facts(root, source=SOURCE):
    path = root / 'sample.py'
    path.write_text(source, encoding='utf-8')
    result = FlowAnalyzer(project_root=root).analyze(FunctionRef('sample', 'public'))
    summary = next(item for item in result.functions if item['function']['qualname'] == 'public')
    return result, summary, path


def test_unknown_documentation_values_do_not_expose_the_fresh_function(tmp_path):
    result, summary, path = facts(tmp_path)
    assert summary['decorator_effects'][0]['body_binding_status'] == 'unknown'
    isolated = summary['fresh_function_decorations'][0]
    assert isolated['body_binding_status'] == 'preserved'
    assert isolated['identity_status'] == 'preserved'
    assert not isolated['boundaries']
    assert isolated['kind'] == 'source_fresh_function_decoration'
    assert isolated['freshness']['phase'] == 'before_name_binding'
    assert isolated['freshness']['input_function_unescaped'] is True
    assert isolated['observation_guard']['source_hashes'] == result.inputs['sha256']
    assert any(effect['operation'] == 'isolated_documentation_format'
               for effect in isolated['effects'])
    namespace = runpy.run_path(str(path))
    assert namespace['public'].__doc__ == 'description'
    with pytest.raises(TypeError):
        namespace['public'](old=1)


@pytest.mark.parametrize('prefix', [
    'opaque(fn)', 'self.saved = fn', 'fn.saved = fn',
    'fn.__code__ = replacement.__code__',
    'self.values["saved"] = fn',
])
def test_an_escaped_or_modified_function_cannot_use_metadata_isolation(tmp_path, prefix):
    _, summary, _ = facts(tmp_path, SOURCE.replace('if fn.__doc__:', prefix + '\n        if fn.__doc__:'))
    assert not summary.get('fresh_function_decorations')


@pytest.mark.parametrize('tail', [
    'import gc\ngc.get_objects()', 'import gc\ngc.get_referrers(known)',
    'import sys\nsys.settrace(opaque)',
    'import sys\ndef observe(): return sys._getframe().f_locals',
])
def test_source_observers_prevent_fresh_function_isolation(tmp_path, tail):
    _, summary, _ = facts(tmp_path, SOURCE + '\n' + tail + '\n')
    assert not summary.get('fresh_function_decorations')


def test_call_target_selection_can_use_the_independent_fresh_binding(tmp_path):
    path = tmp_path / 'sample.py'
    path.write_text(SOURCE + '\ndef client(**kwargs): return public(**kwargs)\n', encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('sample', 'client'), max_depth=2)
    call = next(call for call in result.calls if call.callee_name == 'public')
    assert call.target is not None and call.target.qualname == 'public'
    assert any(item.get('fresh_function_decorations') for item in result.functions)


def test_a_metadata_callback_cannot_change_a_later_function_receiving_helper(tmp_path):
    source = SOURCE.replace('class Cache(dict):', '''def replacement(**kwargs): return kwargs
def preserve(fn): return fn
def alter(fn):
    return replacement
class Cache(dict):''').replace('def __missing__(self, key): return str(key)', '''def __missing__(self, key):
        globals()['preserve'] = alter
        return str(key)''').replace('        return fn', '        return preserve(fn)')
    _, summary, path = facts(tmp_path, source)
    namespace = runpy.run_path(str(path))
    assert namespace['public'](old=1) == {'old': 1}
    assert not summary.get('fresh_function_decorations')


def test_a_class_function_replacement_cannot_reuse_its_source_body(tmp_path):
    source = SOURCE.replace('class Cache(dict):', '''def replacement(**kwargs): return kwargs
def alter(fn):
    return replacement
class Helpers:
    def preserve(fn): return fn
class Cache(dict):''').replace('def __missing__(self, key): return str(key)', '''def __missing__(self, key):
        Helpers.preserve = alter
        return str(key)''').replace('        return fn', '        return Helpers.preserve(fn)')
    _, summary, path = facts(tmp_path, source)
    assert runpy.run_path(str(path))['public'](old=1) == {'old': 1}
    assert not summary.get('fresh_function_decorations')
