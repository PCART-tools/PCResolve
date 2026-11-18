## @package tests.test_class_partial_binding

import ast
from pathlib import Path
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


SOURCE = '''import functools
def mark(name, cls=None):
    if cls is None:
        return functools.partial(mark, name)
    setattr(cls, name, True)
    return cls
def fixed(allowed=0): return allowed
@mark('cache')
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
'''


def setup(root, text=SOURCE):
    path = root / 'example.py'
    path.write_text(text, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    return analyzer, path


def binding(analyzer):
    from pcresolve.flow.proofs._class_partial import bind_partial
    target = analyzer._definition_index.find('example', 'Public', kind='class')[0]
    return bind_partial(analyzer, target, target[1].decorator_list[0])


def test_literal_partial_factory_binds_the_later_class_argument(tmp_path):
    analyzer, path = setup(tmp_path)
    selected = binding(analyzer)
    assert selected is not None
    target, parameter, names, premise = selected
    assert target[0].qualname == 'mark'
    assert parameter == 'cls' and names == {'name': 'cache'}
    assert premise['kind'] == 'source_partial_class_decorator'
    assert premise['runtime_factory_executed'] is False
    assert premise['completion'] == 'normal_factory_return_only'
    assert premise['source_hashes'] == analyzer.hashes
    values = runpy.run_path(str(path))
    assert values['Public'].cache is True
    with pytest.raises(TypeError):
        values['Public'](old=1)
    result = analyzer.analyze(FunctionRef('example', 'Public'))
    fact = result.inputs['entry_binding']['class_decorations'][0]
    assert fact['attributes'] == ['cache']
    assert fact['factory_binding']['kind'] == premise['kind']


@pytest.mark.parametrize('old,new', [
    ('functools.partial(mark, name)', 'opaque(mark, name)'),
    ('functools.partial(mark, name)', 'functools.partial(other, name)'),
    ('functools.partial(mark, name)', 'functools.partial(mark, opaque(name))'),
    ('functools.partial(mark, name)', 'functools.partial(mark, name, cls)'),
    ('if cls is None:', 'if opaque(cls):'),
    ('return functools.partial(mark, name)', 'opaque()\n        return functools.partial(mark, name)'),
    ("@mark('cache')", '@mark(opaque())'),
    ('cls=None', 'cls=opaque()'),
    ('cls=None', 'cls: opaque()=None'),
    ('def mark(name, cls=None):', 'def mark(mark, cls=None):'),
])
def test_unknown_factory_execution_cannot_supply_a_partial_binding(tmp_path, old, new):
    analyzer, _ = setup(tmp_path, SOURCE.replace(old, new))
    assert binding(analyzer) is None


@pytest.mark.parametrize('prefix', [
    'import functools\nfunctools.partial = opaque\n',
    'import functools\nopaque(functools)\n',
    'from functools import partial as captured\nopaque(captured)\n',
    'import functools\nalias = functools.partial\n',
    'import functools\ndef mutate(): functools.partial = opaque\n',
    'import functools\nvars(functools)["partial"] = opaque\n',
])
def test_changed_standard_partial_namespace_keeps_the_factory_unproved(tmp_path, prefix):
    analyzer, _ = setup(tmp_path, prefix + SOURCE)
    assert binding(analyzer) is None


def test_factory_binding_does_not_approve_an_escaping_class_body(tmp_path):
    text = SOURCE.replace('setattr(cls, name, True)', 'opaque(cls)')
    analyzer, _ = setup(tmp_path, text)
    assert binding(analyzer) is not None
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_partial_factory_does_not_hide_a_constructor_slot_write(tmp_path):
    text = SOURCE.replace("@mark('cache')", "@mark('__init__')")
    analyzer, _ = setup(tmp_path, text)
    assert binding(analyzer) is not None
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_readonly_builtin_type_test_does_not_mutate_the_partial_namespace(tmp_path):
    text = SOURCE + '\ndef is_partial(value):\n    return isinstance(value, functools.partial)\n'
    analyzer, _ = setup(tmp_path, text)
    assert binding(analyzer) is not None


def test_shadowed_type_test_does_not_get_the_readonly_builtin_contract(tmp_path):
    text = SOURCE + '\ndef is_partial(value, isinstance):\n    return isinstance(value, functools.partial)\n'
    analyzer, _ = setup(tmp_path, text)
    assert binding(analyzer) is None


def test_replaced_builtin_type_test_cannot_approve_a_namespace_read(tmp_path):
    text = ('import builtins\nbuiltins.isinstance = opaque\n' + SOURCE
            + '\ndef is_partial(value):\n    return isinstance(value, functools.partial)\n')
    analyzer, _ = setup(tmp_path, text)
    assert binding(analyzer) is None


def test_generator_factory_has_no_eager_partial_return(tmp_path):
    text = SOURCE.replace('    return cls', '    yield cls\n    return cls')
    analyzer, _ = setup(tmp_path, text)
    assert binding(analyzer) is None


def test_real_alias_factory_can_be_bound_without_approving_its_effects():
    root = Path('C:/GitHub/VPPDetector/tmp/runtime_matplotlib370/matplotlib')
    if not root.is_dir():
        pytest.skip('Optional real source snapshot is unavailable')
    analyzer = FlowAnalyzer(source_files=[root / 'patches.py', root / '_api/__init__.py',
                                        root / 'artist.py'], import_roots=[root.parent])
    analyzer._index()
    from pcresolve.flow.proofs._class_partial import bind_partial
    target = analyzer._definition_index.find('matplotlib.patches', 'Patch', kind='class')[0]
    expression = next(item for item in target[1].decorator_list if isinstance(item, ast.Call))
    selected = bind_partial(analyzer, target, expression)
    assert selected is not None
    owner, parameter, names, premise = selected
    assert owner[0].qualname == 'define_aliases'
    assert parameter == 'cls' and names == {}
    assert premise['arguments'][0]['value']['kind'] == 'dict'
    assert premise['arguments'][0]['value']['items'][0] == ['antialiased', ['aa']]
