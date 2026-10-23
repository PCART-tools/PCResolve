## @package tests.test_class_literal_loops

import ast
import runpy

import pytest

from pcresolve import FlowAnalyzer, FunctionRef

SOURCE = '''import functools
def alias_table(table, cls=None):
    if cls is None:
        return functools.partial(alias_table, table)
    for field, aliases in table.items():
        for prefix in ['get_', 'set_']:
            for alias in aliases:
                setattr(cls, prefix + alias, True)
    return cls
def fixed(allowed=0): return allowed
@alias_table({'value': ['v', 'val'], 'other': ['o']})
class Public:
    def __init__(self, **kwargs): fixed(**kwargs)
'''


def setup(root, text=SOURCE):
    path = root / 'example.py'
    path.write_text(text, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=root)
    analyzer._index()
    return analyzer, path


def specialized(analyzer):
    from pcresolve._class_partial import bind_partial
    from pcresolve._class_literal_loops import specialize
    target = analyzer._definition_index.find('example', 'Public', kind='class')[0]
    partial = bind_partial(analyzer, target, target[1].decorator_list[0])
    assert partial is not None
    return specialize(analyzer, partial[0], partial[3])


def test_literal_factory_table_supplies_finite_loop_bindings(tmp_path):
    analyzer, path = setup(tmp_path)
    selected = specialized(analyzer)
    assert selected is not None
    function, premise = selected
    assert not any(isinstance(node, ast.For) for node in ast.walk(function))
    assert premise['kind'] == 'source_literal_loop_expansion'
    assert premise['iterations'] == 12
    assert premise['runtime_iterators_executed'] is False
    result = analyzer.analyze(FunctionRef('example', 'Public'))
    fact = result.inputs['entry_binding']['class_decorations'][0]
    assert set(fact['attributes']) == {'get_v', 'get_val', 'set_v', 'set_val', 'get_o', 'set_o'}
    assert fact['literal_loop_expansion']['kind'] == premise['kind']
    values = runpy.run_path(str(path))
    assert values['Public'].get_v is True
    with pytest.raises(TypeError):
        values['Public'](old=1)


@pytest.mark.parametrize('old,new', [
    ('table.items()', 'opaque(table)'),
    ('table.items()', 'table.values()'),
    ('for alias in aliases:', 'for alias in opaque(aliases):'),
    ('for field, aliases in table.items():', 'opaque(table)\n    for field, aliases in table.items():'),
    ('for prefix in', 'aliases.append("bad")\n        for prefix in'),
    ('for prefix in', 'opaque(aliases)\n        for prefix in'),
    ('for prefix in', 'saved = aliases\n        for prefix in'),
    ('for prefix in', 'table.clear()\n        for prefix in'),
    ('for prefix in', 'table = opaque\n        for prefix in'),
    ('for prefix in', 'break\n        for prefix in'),
    ('for prefix in', 'continue\n        for prefix in'),
])
def test_unproved_iteration_or_data_escape_cannot_be_unrolled(tmp_path, old, new):
    analyzer, _ = setup(tmp_path, SOURCE.replace(old, new))
    assert specialized(analyzer) is None


def test_literal_loop_expansion_preserves_unknown_class_effects(tmp_path):
    text = SOURCE.replace('setattr(cls, prefix + alias, True)', 'opaque(cls)')
    analyzer, _ = setup(tmp_path, text)
    assert specialized(analyzer) is not None
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_unrolling_cannot_hide_constructor_slot_writes(tmp_path):
    text = SOURCE.replace("['get_', 'set_']", "['']").replace("['v', 'val']", "['__init__']")
    analyzer, _ = setup(tmp_path, text)
    assert specialized(analyzer) is not None
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_expansion_is_bounded_by_generated_syntax_not_just_input_size(tmp_path):
    analyzer, _ = setup(tmp_path)
    from pcresolve._class_partial import bind_partial
    from pcresolve._class_literal_loops import specialize
    target = analyzer._definition_index.find('example', 'Public', kind='class')[0]
    partial = bind_partial(analyzer, target, target[1].decorator_list[0])
    assert specialize(analyzer, partial[0], partial[3], max_nodes=5) is None


def test_a_new_local_definition_cannot_reuse_the_old_literal_binding(tmp_path):
    text = SOURCE.replace('for field, aliases in table.items():',
                          'def table(): return opaque()\n    for field, aliases in table.items():')
    analyzer, _ = setup(tmp_path, text)
    assert specialized(analyzer) is None


def test_nested_dictionary_keys_are_decoded_without_losing_constructor_writes(tmp_path):
    text = SOURCE[:SOURCE.index('    for field, aliases')] + '''    for outer, nested in table.items():
        for field, value in nested.items():
            setattr(cls, field, True)
    return cls
@alias_table({'outer': {'__init__': True}})
class Public:
    def __init__(self, **kwargs): return None
'''
    analyzer, _ = setup(tmp_path, text)
    assert specialized(analyzer) is not None
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('example', 'Public'))


def test_empty_iterations_do_not_rebind_the_target_names(tmp_path):
    text = SOURCE.replace("{'value': ['v', 'val'], 'other': ['o']}", '{}')
    analyzer, _ = setup(tmp_path, text)
    selected = specialized(analyzer)
    assert selected is not None and selected[1]['iterations'] == 0
    assert not any(isinstance(node, ast.Name) and node.id == 'aliases'
                   and isinstance(node.ctx, ast.Store) for node in ast.walk(selected[0]))


def test_the_real_alias_table_expands_without_discarding_its_closure():
    from pathlib import Path
    from pcresolve._class_partial import bind_partial
    from pcresolve._class_literal_loops import specialize
    root = Path('C:/GitHub/VPPDetector/tmp/runtime_matplotlib370/matplotlib')
    if not root.is_dir():
        pytest.skip('Optional real source snapshot is unavailable')
    analyzer = FlowAnalyzer(source_files=[root / 'patches.py', root / '_api/__init__.py',
                                        root / 'artist.py'], import_roots=[root.parent])
    analyzer._index()
    target = analyzer._definition_index.find('matplotlib.patches', 'Patch', kind='class')[0]
    expression = next(item for item in target[1].decorator_list if isinstance(item, ast.Call))
    partial = bind_partial(analyzer, target, expression)
    assert partial is not None
    selected = specialize(analyzer, partial[0], partial[3])
    assert selected is not None
    function, premise = selected
    assert premise['iterations'] == 25
    assert any(isinstance(node, ast.FunctionDef) and node.name == 'make_alias'
               for node in function.body)
    assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
               and node.func.id == 'make_alias' for node in ast.walk(function))


@pytest.mark.parametrize('replacement', [
    'global aliases\n    for field, aliases in table.items():',
    'for field, aliases in table.items():\n        try:\n            break\n        except Exception:\n            pass',
])
def test_control_or_scope_changes_cannot_turn_iteration_into_fresh_local_assignments(tmp_path, replacement):
    analyzer, _ = setup(tmp_path, SOURCE.replace('for field, aliases in table.items():', replacement))
    assert specialized(analyzer) is None
