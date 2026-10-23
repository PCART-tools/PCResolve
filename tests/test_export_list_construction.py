## @package tests.test_export_list_construction

import pytest

from pcresolve._export_lists import ExportListResolver


def put(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def test_export_lists_compose_literals_and_imported_lists_without_importing(tmp_path):
    put(tmp_path, 'pkg/__init__.py', '''from . import one, two
__all__ = ['own']
__all__ += one.__all__
__all__.extend(two.__all__)
__all__.append('last')
__all__.remove('discard')
raise RuntimeError('Source must never be executed')
''')
    put(tmp_path, 'pkg/one.py', "__all__ = ['first', 'discard']\n")
    put(tmp_path, 'pkg/two.py', "__all__ = ('second',)\n")
    fact = ExportListResolver([tmp_path]).resolve('pkg')
    assert fact['values'] == ['own', 'first', 'second', 'last']
    assert fact['container_kind'] == 'list'
    assert fact['namespace_binding_proven'] is False
    assert fact['runtime_exports_confirmed'] is False
    assert fact['scope'] == 'finite_source_export_list_construction'
    assert len(fact['source_hashes']) == 3
    assert len(fact['construction_evidence']) == 7


@pytest.mark.parametrize('text', [
    "__all__ = ['before']\n__all__ = __all__ + ['after']\n",
    "__all__ = ('before',)\n__all__ += ('after',)\n",
])
def test_ordered_native_sequence_reconstruction(tmp_path, text):
    put(tmp_path, 'example.py', text)
    assert ExportListResolver([tmp_path]).resolve('example')['values'] == ['before', 'after']


@pytest.mark.parametrize('tail', [
    "saved = __all__", "opaque(__all__)", "__all__.sort()",
    "__all__[0] = 'other'", "del __all__", "__all__ = opaque()",
    "__all__ += opaque", "__all__.extend(opaque)",
    "__all__.append(opaque)", "__all__.remove('missing')",
    "def mutate(): __all__.append('later')",
    "def mutate():\n    global __all__\n    __all__ = ['later']",
])
def test_open_aliases_mutations_and_runtime_export_writes_supply_no_list(tmp_path, tail):
    put(tmp_path, 'example.py', "__all__ = ['before']\n" + tail + '\n')
    assert ExportListResolver([tmp_path]).resolve('example') is None


def test_import_alias_rebinding_does_not_reuse_a_module_export_list(tmp_path):
    put(tmp_path, 'one.py', "__all__ = ['a']\n")
    put(tmp_path, 'example.py', 'import one\none = opaque\n__all__ = one.__all__\n')
    assert ExportListResolver([tmp_path]).resolve('example') is None


def test_borrowed_list_mutation_cannot_reuse_a_dependency_snapshot(tmp_path):
    put(tmp_path, 'one.py', "__all__ = ['a']\n")
    put(tmp_path, 'example.py', "import one\n__all__ = one.__all__\n__all__.append('b')\n")
    assert ExportListResolver([tmp_path]).resolve('example') is None


def test_an_imported_list_mutation_is_not_a_local_construction(tmp_path):
    put(tmp_path, 'one.py', "__all__ = ['a']\n")
    put(tmp_path, 'example.py', "import one\none.__all__.append('b')\n__all__ = one.__all__\n")
    assert ExportListResolver([tmp_path]).resolve('example') is None


def test_foreign_module_introspection_does_not_prove_or_alias_this_export_list(tmp_path):
    put(tmp_path, 'example.py', "__all__ = ['a']\ndef describe(other): return other.__all__\n")
    fact = ExportListResolver([tmp_path]).resolve('example')
    assert fact['values'] == ['a']
    assert fact['namespace_binding_proven'] is False


def test_imported_export_list_aliases_remain_outside_the_construction_grammar(tmp_path):
    put(tmp_path, 'one.py', "__all__ = ['a']\n")
    put(tmp_path, 'example.py', "import one\n__all__ = ['own']\nsaved = one.__all__\n")
    assert ExportListResolver([tmp_path]).resolve('example') is None


def test_cycles_and_ambiguous_module_paths_do_not_choose_a_source(tmp_path):
    put(tmp_path, 'one.py', 'import two\n__all__ = two.__all__\n')
    put(tmp_path, 'two.py', 'import one\n__all__ = one.__all__\n')
    assert ExportListResolver([tmp_path]).resolve('one') is None
    put(tmp_path, 'one/__init__.py', "__all__ = ['other']\n")
    assert ExportListResolver([tmp_path]).resolve('one') is None


def test_each_resolve_captures_fresh_sources_and_retains_old_facts(tmp_path):
    path = put(tmp_path, 'example.py', "__all__ = ['first']\n")
    reader = ExportListResolver([tmp_path])
    before = reader.resolve('example')
    path.write_text("__all__ = ['after']\n")
    after = reader.resolve('example')
    assert before['values'] == ['first'] and after['values'] == ['after']
    assert before['source_hashes'] != after['source_hashes']


def test_exhaustion_does_not_release_part_of_an_export_list(tmp_path):
    put(tmp_path, 'example.py', "__all__ = ['first', 'second']\n")
    assert ExportListResolver([tmp_path], max_nodes=1).resolve('example') is None
    assert ExportListResolver([tmp_path], max_names=1).resolve('example') is None


@pytest.mark.parametrize('module', ['../outside', 'pkg..name', '/absolute', 'pkg/name'])
def test_module_identifiers_cannot_select_paths_outside_import_roots(tmp_path, module):
    assert ExportListResolver([tmp_path]).resolve(module) is None


def test_direct_package_module_inputs_have_separate_import_binding_evidence(tmp_path):
    put(tmp_path, 'pkg/__init__.py', 'from . import one\n__all__ = ["own"] + one.__all__\n')
    put(tmp_path, 'pkg/one.py', '__all__ = ["child"]\n')
    fact = ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True)
    assert fact['values'] == ['own', 'child']
    assert fact['module_inputs_proven'] is True
    assert len(fact['module_input_bindings']) == 1
    proof = fact['module_input_bindings'][0]
    assert proof['target_module'] == 'pkg.one'
    assert proof['completion'] == 'normal_import_return_only'
    assert proof['runtime_module_confirmed'] is False
    assert fact['namespace_binding_proven'] is False


@pytest.mark.parametrize('statement', ['from .one import *', 'from pkg.one import *'])
def test_child_star_import_can_supply_its_parent_package_module_binding(tmp_path, statement):
    put(tmp_path, 'pkg/__init__.py', statement + '\n__all__ = [] + one.__all__\n')
    put(tmp_path, 'pkg/one.py', '__all__ = ["child"]\nchild = 1\n')
    fact = ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True)
    assert fact is not None
    assert fact['values'] == ['child']
    proof = fact['module_input_bindings'][0]
    assert proof['binding_protocol'] == 'implicit_parent_submodule_attribute'
    assert proof['target_module'] == 'pkg.one'
    assert proof['completion'] == 'normal_import_return_only'
    assert proof['runtime_module_confirmed'] is False
    assert fact['namespace_binding_proven'] is False


@pytest.mark.parametrize('prefix,child,tail', [
    ('one = opaque\n', '', ''),
    ('', '', 'del one\n'),
    ('', '', 'def mutate():\n    global one\n    one = opaque\n'),
    ('', '__all__ = ["one"]\none = opaque\n', ''),
    ('from .two import *\n', '', ''),
    ('', '', 'from .two import *\n'),
    ('', 'import pkg\npkg.one = opaque\n', ''),
    ('', 'import pkg as parent\nopaque(parent)\n', ''),
    ('', 'import sys\nsys.modules[__name__] = opaque\n', ''),
    ('', '', 'globals()["one"] = opaque\n'),
    ('__path__ = opaque\n', '', ''),
    ('__path__.append(opaque)\n', '', ''),
    ('__spec__ = opaque\n', '', ''),
    ('', 'import pkg\npkg.__path__.append(opaque)\n', ''),
])
def test_implicit_child_binding_does_not_ignore_cache_shadowing_or_namespace_effects(
        tmp_path, prefix, child, tail):
    put(tmp_path, 'pkg/__init__.py', prefix + 'from .one import *\n' + tail
        + '__all__ = [] + one.__all__\n')
    put(tmp_path, 'pkg/one.py', '__all__ = ["child"]\nchild = 1\n' + child)
    put(tmp_path, 'pkg/two.py', '__all__ = ["one"]\none = opaque\n')
    assert ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True) is None


def test_a_child_star_in_an_ordinary_module_does_not_bind_a_sibling_name(tmp_path):
    put(tmp_path, 'pkg/__init__.py', '')
    put(tmp_path, 'pkg/one.py', '__all__ = ["child"]\n')
    put(tmp_path, 'pkg/other.py', 'from .one import *\n__all__ = [] + one.__all__\n')
    assert ExportListResolver([tmp_path]).resolve('pkg.other', validate_module_inputs=True) is None


def test_explicit_and_implicit_child_module_inputs_can_coexist(tmp_path):
    put(tmp_path, 'pkg/__init__.py', 'from . import one\nfrom .one import *\n'
        'from .two import *\n__all__ = [] + one.__all__ + two.__all__\n')
    put(tmp_path, 'pkg/one.py', '__all__ = ["first"]\n')
    put(tmp_path, 'pkg/two.py', '__all__ = ["second"]\n')
    fact = ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True)
    assert fact is not None and fact['values'] == ['first', 'second']


def test_a_same_named_class_before_a_relative_import_is_not_a_module_input(tmp_path):
    put(tmp_path, 'pkg/__init__.py', '''class one:
    __all__ = ['class_value']
from . import one
__all__ = one.__all__
''')
    put(tmp_path, 'pkg/one.py', "__all__ = ['file_value']\n")
    assert ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True) is None


def test_parent_module_getattr_makes_relative_import_input_unproven(tmp_path):
    put(tmp_path, 'pkg/__init__.py', '''def __getattr__(name): return opaque
from . import one
__all__ = one.__all__
''')
    put(tmp_path, 'pkg/one.py', "__all__ = ['child']\n")
    assert ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True) is None


def test_known_star_exports_before_a_submodule_import_do_not_shadow_its_name(tmp_path):
    put(tmp_path, 'pkg/__init__.py', '''from .one import *
from . import one
__all__ = one.__all__
''')
    put(tmp_path, 'pkg/one.py', "__all__ = ['child']\n")
    assert ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True)


def test_star_exports_can_shadow_the_later_submodule_name(tmp_path):
    put(tmp_path, 'pkg/__init__.py', '''from .one import *
from . import one
__all__ = one.__all__
''')
    put(tmp_path, 'pkg/one.py', "__all__ = ['one']\none = opaque\n")
    assert ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True) is None


@pytest.mark.parametrize('prefix', [
    "globals()['one'] = opaque",
    'import pkg as parent\nparent.one = opaque',
    'import pkg as parent\nsaved = parent\nsaved.one = opaque',
    "import sys\nsys.modules['pkg.one'] = opaque",
    "def mutate():\n    global one\n    one = opaque\nmutate()",
    'def mutate():\n    import pkg as parent\n    parent.one = opaque\nmutate()',
    'def mutate():\n    import pkg as parent\n    parent.one = opaque\n'
    'def other():\n    import foreign as parent\nmutate()',
])
def test_package_namespace_writes_before_import_do_not_become_module_inputs(tmp_path, prefix):
    put(tmp_path, 'pkg/__init__.py', prefix + '\nfrom . import one as values\n'
        '__all__ = values.__all__\n')
    put(tmp_path, 'pkg/one.py', "__all__ = ['child']\n")
    assert ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True) is None


@pytest.mark.parametrize('prefix', [
    "import sys\nsys.modules[__name__] = opaque",
    "import sys\nsys.modules.update({__name__: opaque})",
    "import sys\nregistry = sys.modules\nregistry[__name__] = opaque",
    "import sys\nsys.modules[__name__].__class__ = opaque",
    "import sys\nsetattr(sys.modules[__name__], '__class__', opaque)",
    "import sys\ngetattr(sys, 'modules')[__name__] = opaque",
    "__import__('sys').modules[__name__] = opaque",
    'import sys\nsys.modules = opaque',
])
def test_source_module_replacement_prevents_import_input_certainty(tmp_path, prefix):
    put(tmp_path, 'pkg/__init__.py', 'from . import one\n__all__ = one.__all__\n')
    put(tmp_path, 'pkg/one.py', prefix + "\n__all__ = ['child']\n")
    assert ExportListResolver([tmp_path]).resolve('pkg', validate_module_inputs=True) is None
