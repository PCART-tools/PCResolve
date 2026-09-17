## @package tests.test_import_facts
#  Import facts preserve raw syntax and explicit adapter binding policies.

import ast
from dataclasses import FrozenInstanceError

import pytest

from pcresolve.import_facts import import_facts, resolve_relative_module


def test_plain_import_retains_python_and_ownership_compatibility_bindings():
    node = ast.parse('import package.sub, other.module as alias').body[0]
    facts = import_facts(node)
    assert [(fact.kind, fact.name, fact.asname) for fact in facts] == [
        ('import', 'package.sub', None),
        ('import', 'other.module', 'alias'),
    ]
    assert [fact.python_binding for fact in facts] == ['package', 'alias']
    assert [fact.full_binding for fact in facts] == [
        'package.sub', 'alias']
    with pytest.raises(FrozenInstanceError):
        facts[0].name = 'changed'


def test_from_import_retains_level_module_alias_and_wildcard():
    relative = import_facts(
        ast.parse('from ..helpers import run as execute').body[0])[0]
    wildcard = import_facts(ast.parse('from package import *').body[0])[0]
    assert (relative.kind, relative.module, relative.level,
            relative.name, relative.python_binding) == (
                'from', 'helpers', 2, 'run', 'execute')
    assert wildcard.wildcard and wildcard.python_binding == '*'


def test_relative_module_resolution_distinguishes_modules_and_packages():
    assert resolve_relative_module(
        'pkg.feature.main', False, 'helpers', 1) == 'pkg.feature.helpers'
    assert resolve_relative_module(
        'pkg.feature.main', False, 'helpers', 2) == 'pkg.helpers'
    assert resolve_relative_module(
        'pkg.feature', True, 'helpers', 1) == 'pkg.feature.helpers'
    assert resolve_relative_module(
        'pkg.feature.main', False, None, 1) == 'pkg.feature'
    assert resolve_relative_module(
        'main', False, 'helpers', 3) == 'helpers'
    assert resolve_relative_module(
        '', False, 'helpers', 1) == 'helpers'


def test_non_import_nodes_have_no_import_facts():
    assert import_facts(ast.parse('value = 1').body[0]) == ()
