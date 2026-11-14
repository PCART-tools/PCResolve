## @package tests.test_shared_layer_boundaries
#  Architectural dependency direction for the shared program-fact layer.
import ast
import importlib.util
from pathlib import Path
import pytest

PACKAGE = Path(__file__).parents[1] / 'src' / 'pcresolve'


def _module(path):
    parts = list(path.relative_to(PACKAGE).with_suffix('').parts)
    if parts[-1] == '__init__':
        parts.pop()
    return '.'.join(['pcresolve'] + parts)


def _local_imports(path, include_dynamic=True):
    name = _module(path)
    package = name if path.name == '__init__.py' else name.rpartition('.')[0]
    modules = {_module(source) for source in PACKAGE.rglob('*.py')}
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    imports = set()
    dynamic_names = {'__import__'}
    importlib_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'importlib':
            dynamic_names.update(alias.asname or alias.name for alias in node.names
                                 if alias.name == 'import_module')
        elif isinstance(node, ast.Import):
            importlib_names.update(alias.asname or alias.name for alias in node.names
                                   if alias.name == 'importlib')
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                target = importlib.util.resolve_name('.' * node.level + (node.module or ''), package)
            else:
                target = node.module or ''
            if target == 'pcresolve' or target.startswith('pcresolve.'):
                imports.add(target)
                for alias in node.names:
                    candidate = target + '.' + alias.name
                    if candidate in modules:
                        imports.add(candidate)
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names if alias.name.startswith('pcresolve.'))
        elif (include_dynamic and isinstance(node, ast.Call) and
              (isinstance(node.func, ast.Name) and node.func.id in dynamic_names or
               isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module'
               and isinstance(node.func.value, ast.Name) and node.func.value.id in importlib_names)):
            names = [keyword.value for keyword in node.keywords if keyword.arg == 'name']
            if not node.args and len(names) != 1:
                raise AssertionError('%s:%s: unresolved dynamic import' % (path, node.lineno))
            value = node.args[0] if node.args else names[0]
            if (isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add)
                    and isinstance(value.left, ast.Name) and value.left.id == '__package__'
                    and isinstance(value.right, ast.Constant)
                    and isinstance(value.right.value, str)):
                imports.add(package + value.right.value)
            elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                target = value.value
                if target.startswith('.'):
                    target = importlib.util.resolve_name(target, package)
                if target == 'pcresolve' or target.startswith('pcresolve.'):
                    imports.add(target)
            elif (name == 'pcresolve.runtime._legacy_imports'
                  or name == 'pcresolve' and path.name == '__init__.py'):
                # Lazy compatibility imports target this finite explicit map.
                from pcresolve.runtime._legacy_imports import _MOVED_MODULES, _RENAMED_MODULES, _NESTED_MOVES
                imports.update('pcresolve.' + target for target in _RENAMED_MODULES.values())
                imports.update('pcresolve.' + target for target in _NESTED_MOVES.values())
                imports.update('pcresolve.' + namespace + '.' + item
                               for namespace, items in _MOVED_MODULES.items() for item in items)
            else:
                raise AssertionError('%s:%s: unresolved dynamic import' % (path, node.lineno))
    return imports


def test_shared_fact_modules_do_not_depend_on_analyzer_adapters():
    for directory in ('frontend', 'facts'):
        for path in (PACKAGE / directory).rglob('*.py'):
            for dependency in _local_imports(path):
                assert not dependency.startswith(('pcresolve.ownership', 'pcresolve.flow')), (path, dependency)


def test_analyzers_consume_the_shared_layer_through_explicit_imports():
    for directory in ('ownership', 'flow'):
        imports = set().union(*(_local_imports(path) for path in (PACKAGE / directory).rglob('*.py')))
        assert any(name.startswith('pcresolve.frontend.') for name in imports)
        assert any(name.startswith('pcresolve.facts.') for name in imports)


def _assert_package_import_graph_acyclic(include_dynamic):
    paths = tuple(PACKAGE.rglob('*.py'))
    modules = {_module(path) for path in paths}
    graph = {_module(path): _local_imports(path, include_dynamic) & modules for path in paths}
    visited = set()
    active = []

    def visit(module):
        if module in active:
            raise AssertionError(' -> '.join(active[active.index(module):] + [module]))
        if module in visited:
            return
        active.append(module)
        for dependency in sorted(graph[module]):
            visit(dependency)
        active.pop()
        visited.add(module)

    for module in sorted(graph):
        visit(module)


def test_internal_static_import_graph_is_acyclic():
    _assert_package_import_graph_acyclic(include_dynamic=False)


def test_internal_complete_import_graph_is_acyclic():
    _assert_package_import_graph_acyclic(include_dynamic=True)


def _assert_compatibility_layer_is_a_sink():
    compatibility = 'pcresolve.runtime._legacy_imports'
    for path in PACKAGE.rglob('*.py'):
        module = _module(path)
        if module in ('pcresolve', compatibility):
            continue
        for dependency in _local_imports(path):
            assert dependency != compatibility and not dependency.startswith(compatibility + '.'), (
                path, dependency)


def test_implementation_modules_do_not_import_the_compatibility_layer():
    _assert_compatibility_layer_is_a_sink()


def test_compatibility_layer_reverse_import_is_detected(tmp_path, monkeypatch):
    package = tmp_path / 'pcresolve'
    (package / 'ownership').mkdir(parents=True)
    (package / 'runtime').mkdir()
    (package / 'ownership' / 'probe.py').write_text(
        'import pcresolve.runtime._legacy_imports\n', encoding='utf-8')
    monkeypatch.setitem(globals(), 'PACKAGE', package)
    with pytest.raises(AssertionError, match='_legacy_imports'):
        _assert_compatibility_layer_is_a_sink()


def test_dynamic_package_import_is_included_in_dependency_graph():
    source = PACKAGE / 'flow' / 'proofs' / 'classes' / '_class_creation.py'
    assert 'pcresolve.flow.proofs.classes._class_creation_calls' in _local_imports(source)


def test_static_import_cycle_is_detected_in_synthetic_package(tmp_path, monkeypatch):
    package = tmp_path / 'pcresolve'
    package.mkdir()
    (package / 'a.py').write_text('from pcresolve import b\n', encoding='utf-8')
    (package / 'b.py').write_text('from pcresolve import a\n', encoding='utf-8')
    monkeypatch.setitem(globals(), 'PACKAGE', package)
    with pytest.raises(AssertionError, match='pcresolve.a'):
        _assert_package_import_graph_acyclic(include_dynamic=True)


def test_dynamic_import_cycle_is_detected_in_synthetic_package(tmp_path, monkeypatch):
    package = tmp_path / 'pcresolve'
    package.mkdir()
    (package / 'a.py').write_text(
        "from importlib import import_module\nimport_module(__package__ + '.b')\n", encoding='utf-8')
    (package / 'b.py').write_text('from pcresolve import a\n', encoding='utf-8')
    monkeypatch.setitem(globals(), 'PACKAGE', package)
    with pytest.raises(AssertionError, match='pcresolve.a'):
        _assert_package_import_graph_acyclic(include_dynamic=True)


def test_unresolved_dynamic_import_is_reported(tmp_path, monkeypatch):
    package = tmp_path / 'pcresolve'
    package.mkdir()
    source = package / 'a.py'
    source.write_text('from importlib import import_module\nimport_module(dynamic_name)\n', encoding='utf-8')
    monkeypatch.setitem(globals(), 'PACKAGE', package)
    with pytest.raises(AssertionError, match='unresolved dynamic import'):
        _local_imports(source)


@pytest.mark.parametrize('statement', [
    "from importlib import import_module as load\nload('pcresolve.flow.analyzer')",
    "import importlib as imports\nimports.import_module('pcresolve.flow.analyzer')",
    "__import__('pcresolve.flow.analyzer')",
    "from importlib import import_module\nimport_module(name='pcresolve.flow.analyzer')",
])
def test_dynamic_import_forms_are_detected(tmp_path, monkeypatch, statement):
    package = tmp_path / 'pcresolve'
    package.mkdir()
    source = package / 'a.py'
    source.write_text(statement + '\n', encoding='utf-8')
    monkeypatch.setitem(globals(), 'PACKAGE', package)
    assert 'pcresolve.flow.analyzer' in _local_imports(source)


def test_module_effect_core_does_not_depend_on_class_creation_calls():
    core = PACKAGE / 'flow' / 'proofs' / 'namespaces' / 'modules' / '_module_class_effects_core.py'
    assert 'pcresolve.flow.proofs.classes._class_creation_calls' not in _local_imports(core)
    caller = PACKAGE / 'flow' / 'proofs' / 'classes' / '_class_creation_calls.py'
    assert 'pcresolve.flow.proofs.namespaces.modules._module_class_effects' not in _local_imports(caller)


def _assert_analyzers_do_not_import_each_other():
    for directory, forbidden in (('ownership', 'pcresolve.flow'), ('flow', 'pcresolve.ownership')):
        for path in (PACKAGE / directory).rglob('*.py'):
            for dependency in _local_imports(path):
                assert dependency != forbidden and not dependency.startswith(forbidden + '.'), (path, dependency)


def test_analyzers_do_not_import_each_other():
    _assert_analyzers_do_not_import_each_other()


@pytest.mark.parametrize(('source', 'dependency'), [
    ('ownership', 'flow'), ('flow', 'ownership'),
])
def test_cross_analyzer_dependency_is_detected(tmp_path, monkeypatch, source, dependency):
    package = tmp_path / 'pcresolve'
    for directory in ('ownership', 'flow'):
        (package / directory).mkdir(parents=True)
    (package / source / 'probe.py').write_text(
        'def probe():\n    import pcresolve.%s\n' % dependency, encoding='utf-8')
    monkeypatch.setitem(globals(), 'PACKAGE', package)
    with pytest.raises(AssertionError):
        _assert_analyzers_do_not_import_each_other()
