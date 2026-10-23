## @package tests.test_source_binding_selection

import pytest

from pcresolve._source_bindings import SourceBindingResolver


def put(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def test_public_binding_follows_composed_exports_without_claiming_function_identity(tmp_path):
    put(tmp_path, 'pkg/lib/__init__.py',
        'from . import impl\nfrom .impl import *\n__all__ = [] + impl.__all__\n')
    put(tmp_path, 'pkg/lib/impl.py', "__all__ = ['public']\n@decorate\ndef public(value): return value\n")
    put(tmp_path, 'pkg/__init__.py', 'if setup:\n    pass\nelse:\n    from .lib import *\n')
    fact = SourceBindingResolver([tmp_path]).resolve('pkg', 'public')
    assert fact['status'] == 'unique_declaration_when_lookup_succeeds'
    assert fact['target']['module'] == 'pkg.lib.impl'
    assert fact['target']['qualname'] == 'public'
    assert fact['may_be_unbound'] is True
    assert fact['runtime_target_confirmed'] is False
    assert fact['callable_identity_proven'] is False
    assert fact['body_binding_proven'] is False
    assert fact['paths'][0]['conditions']
    assert len(fact['source_hashes']) == 3


def test_direct_definition_is_a_source_declaration_reference(tmp_path):
    put(tmp_path, 'example.py', 'def public(value): return value\n')
    fact = SourceBindingResolver([tmp_path]).resolve('example', 'public')
    assert fact['may_be_unbound'] is False
    assert fact['target']['lineno'] == 1


@pytest.mark.parametrize('text', [
    'if flag:\n    def public(): pass\nelse:\n    def public(): pass\n',
    'def public(): pass\npublic = opaque\n',
    'def public(): pass\nfrom missing import *\n',
    'if flag:\n    def public(): pass\nelse:\n    def __getattr__(name): return opaque\n',
    'def public(): pass\ndef later():\n    global public\n    public = opaque\n',
    "def public(): pass\nglobals()['public'] = opaque\n",
    "def public(): pass\nnamespace = globals()\nnamespace['public'] = opaque\n",
    "import sys\ndef public(): pass\nsys.modules[__name__] = opaque\n",
    "import sys\ndef public(): pass\ngetattr(sys, 'modules')[__name__] = opaque\n",
    "from sys import modules as registry\ndef public(): pass\nregistry[__name__] = opaque\n",
    "from builtins import globals as namespace\ndef public(): pass\nnamespace()['public'] = opaque\n",
    "import example as own\ndef public(): pass\nsetattr(own, 'public', opaque)\n",
    'import example as own\ndef public(): pass\nsaved = own\nsaved.public = opaque\n',
    'import example as own\ndef public(): pass\nown.public = opaque\n',
    'def public(): pass\nexec(code)\n',
    'def public(): pass\nif (public := opaque):\n    pass\n',
    "import sys\ndef public(): pass\nfield = 'modules'\ngetattr(sys, field)[__name__] = opaque\n",
    "from importlib import import_module as load\ndef public(): pass\n"
    "setattr(load(__name__), 'public', opaque)\n",
    "namespace = __builtins__\nnamespace['__import__'] = opaque\nfrom impl import public\n",
])
def test_open_or_competing_bindings_do_not_select_a_declaration(tmp_path, text):
    put(tmp_path, 'example.py', text)
    put(tmp_path, 'impl.py', 'def public(): pass\n')
    assert SourceBindingResolver([tmp_path]).resolve('example', 'public') is None


def test_later_known_binding_overwrites_an_earlier_unknown_star(tmp_path):
    put(tmp_path, 'example.py', 'from missing import *\ndef public(): pass\n')
    assert SourceBindingResolver([tmp_path]).resolve('example', 'public')


def test_later_known_star_without_name_preserves_the_prior_binding(tmp_path):
    put(tmp_path, 'example.py', 'def public(): pass\nfrom other import *\n')
    put(tmp_path, 'other.py', "__all__ = ['different']\ndef different(): pass\n")
    assert SourceBindingResolver([tmp_path]).resolve('example', 'public')


def test_getattr_is_irrelevant_on_paths_where_the_attribute_is_bound(tmp_path):
    put(tmp_path, 'example.py', 'if flag:\n    def public(): pass\n'
        '    def __getattr__(name): return opaque\n')
    fact = SourceBindingResolver([tmp_path]).resolve('example', 'public')
    assert fact['may_be_unbound']


def test_conditional_deletion_retains_the_missing_lookup_path(tmp_path):
    put(tmp_path, 'example.py', 'def public(): pass\nif flag:\n    del public\n')
    assert SourceBindingResolver([tmp_path]).resolve('example', 'public')['may_be_unbound']


def test_named_reexports_are_followed_with_aliases(tmp_path):
    put(tmp_path, 'example.py', 'from impl import private as public\n')
    put(tmp_path, 'impl.py', 'def private(): pass\n')
    fact = SourceBindingResolver([tmp_path]).resolve('example', 'public')
    assert fact['target']['module'] == 'impl'
    assert fact['target']['qualname'] == 'private'


def test_finite_globals_writes_preserve_an_unrelated_explicit_reexport(tmp_path):
    put(tmp_path, 'example.py',
        'from impl import public\n'
        "for alias in ('float96', 'complex192'):\n"
        '    globals()[alias] = opaque\n')
    put(tmp_path, 'impl.py', 'def public(): pass\n')
    fact = SourceBindingResolver([tmp_path]).resolve('example', 'public')
    assert fact is not None
    assert fact['target']['module'] == 'impl'
    assert fact['target']['qualname'] == 'public'


@pytest.mark.parametrize('keys', ["('public',)", 'dynamic_keys'])
def test_globals_writes_with_a_matching_or_open_key_remain_unknown(tmp_path, keys):
    put(tmp_path, 'example.py',
        f'from impl import public\nfor alias in {keys}:\n'
        '    globals()[alias] = opaque\n')
    put(tmp_path, 'impl.py', 'def public(): pass\n')
    assert SourceBindingResolver([tmp_path]).resolve('example', 'public') is None


def test_import_cycles_and_source_ambiguity_remain_open(tmp_path):
    put(tmp_path, 'one.py', 'from two import public\n')
    put(tmp_path, 'two.py', 'from one import public\n')
    assert SourceBindingResolver([tmp_path]).resolve('one', 'public') is None
    put(tmp_path, 'one.py', 'def public(): pass\n')
    put(tmp_path, 'one/__init__.py', 'def public(): pass\n')
    assert SourceBindingResolver([tmp_path]).resolve('one', 'public') is None


def test_snapshots_and_budgets_do_not_reuse_stale_or_partial_proofs(tmp_path):
    path = put(tmp_path, 'example.py', 'def public(): pass\n')
    resolver = SourceBindingResolver([tmp_path])
    before = resolver.resolve('example', 'public')
    path.write_text('public = opaque\n', encoding='utf-8')
    assert resolver.resolve('example', 'public') is None
    assert before['target']['qualname'] == 'public'
    assert SourceBindingResolver([tmp_path], max_nodes=1).resolve('example', 'public') is None


def test_normal_completion_does_not_invent_a_value_after_unconditional_raise(tmp_path):
    put(tmp_path, 'example.py', 'raise Error\ndef public(): pass\n')
    assert SourceBindingResolver([tmp_path]).resolve('example', 'public') is None


def test_star_construction_work_shares_the_outer_query_budget(tmp_path):
    put(tmp_path, 'example.py', 'from other import *\ndef public(): pass\n')
    put(tmp_path, 'other.py', '__all__ = [' + ','.join(repr('name' + str(i))
                                                    for i in range(100)) + ']\n')
    assert SourceBindingResolver([tmp_path], max_nodes=80).resolve('example', 'public') is None
