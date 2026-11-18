## @package tests.test_static_star_imports

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


def test_no_top_level_wildcards_need_no_namespace_tree_scan(monkeypatch):
    import ast
    from pcresolve.facts.star_imports import static_star_imports
    tree = ast.parse('import dependency\ndef api():\n    return dependency.run()\n')
    def unexpected(*args):
        raise AssertionError('No wildcard binding can be introduced')
    with monkeypatch.context() as context:
        context.setattr(ast, 'walk', unexpected)
        result = static_star_imports({'module': [('module.py', tree.body)]})
    assert result.aliases == result.bindings == {}


def package(tmp_path, public='from .impl import *\n', implementation=None):
    root = tmp_path / 'pkg'
    root.mkdir()
    (root / '__init__.py').write_text(public, encoding='utf-8')
    (root / 'impl.py').write_text(implementation or '''__all__ = ['Entry', 'api']
def fixed(allowed=0):
    return None
class Entry:
    def __init__(self, **kwargs):
        fixed(**kwargs)
def api(**kwargs):
    return fixed(**kwargs)
''', encoding='utf-8')
    return root


@pytest.mark.parametrize('name,target', [('Entry', 'Entry.__init__'), ('api', 'api')])
def test_literal_star_exports_resolve_public_entry_names(tmp_path, name, target):
    package(tmp_path)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', name))
    assert result.entry.module == 'pkg.impl'
    assert result.entry.qualname == target
    assert result.find_calls(callee_name='fixed')


def test_nested_star_exports_retain_their_source_binding(tmp_path):
    root = package(tmp_path, 'from .middle import *\n')
    (root / 'middle.py').write_text(
        "from .impl import *\n__all__ = ['Entry', 'api']\n", encoding='utf-8')
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', 'Entry'))
    assert result.entry.module == 'pkg.impl'
    assert result.inputs['entry_binding']['status'] == 'source_bound'


@pytest.mark.parametrize('extra', [
    'Entry = unknown\n',
    'del Entry\n',
    'from .unknown import *\n',
    "exec('Entry = unknown')\n",
])
def test_conflicting_or_open_public_namespaces_do_not_select_an_export(tmp_path, extra):
    package(tmp_path, 'from .impl import *\n' + extra)
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', 'Entry'))


@pytest.mark.parametrize('all_text', [
    '__all__ = choose_names()\n',
    "__all__ = ['Entry']\n__all__.append('other')\n",
    "__all__ = ['Entry']\nalias = __all__\n",
])
def test_dynamic_or_mutable_export_lists_do_not_supply_aliases(tmp_path, all_text):
    package(tmp_path, implementation=all_text + 'class Entry:\n    def __init__(self): pass\n')
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', 'Entry'))


def test_star_import_cycles_do_not_invent_a_definition(tmp_path):
    root = package(tmp_path, 'from .middle import *\n')
    (root / 'middle.py').write_text(
        "from . import *\n__all__ = ['Entry']\n", encoding='utf-8')
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', 'Entry'))


def test_duplicate_star_names_remain_ambiguous(tmp_path):
    root = package(tmp_path, 'from .impl import *\nfrom .other import *\n')
    (root / 'other.py').write_text(
        "__all__ = ['Entry']\nclass Entry:\n    def __init__(self): pass\n", encoding='utf-8')
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', 'Entry'))


def test_exported_name_rebound_in_its_definition_module_is_not_the_old_class(tmp_path):
    package(tmp_path, implementation="""__all__ = ['Entry']
class Entry:
    def __init__(self): pass
Entry = unknown
""")
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', 'Entry'))


@pytest.mark.parametrize('mutation', [
    'impl.Entry = unknown',
    'del impl.Entry',
    "impl.__all__.append('other')",
    "setattr(impl, 'Entry', unknown)",
    "setattr(impl, dynamic_name, unknown)",
    'alias = impl\nalias.Entry = unknown',
    'mutate(impl)',
])
def test_imported_module_mutation_invalidates_export_proof(tmp_path, mutation):
    package(tmp_path, 'from . import impl\n' + mutation + '\nfrom .impl import *\n')
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', 'Entry'))


def test_import_star_export_list_rebinding_remains_open(tmp_path):
    package(tmp_path, implementation="""__all__ = ['Entry']
class Entry:
    def __init__(self): pass
del __all__
""")
    with pytest.raises(ValueError):
        FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('pkg', 'Entry'))


def test_source_export_edits_refresh_analyzer_alias_facts(tmp_path):
    root = package(tmp_path)
    analyzer = FlowAnalyzer(project_root=tmp_path)
    assert analyzer.analyze(FunctionRef('pkg', 'Entry')).entry.module == 'pkg.impl'
    path = root / 'impl.py'
    path.write_text(path.read_text(encoding='utf-8') + '\nEntry = unknown\n', encoding='utf-8')
    with pytest.raises(ValueError):
        analyzer.analyze(FunctionRef('pkg', 'Entry'))
