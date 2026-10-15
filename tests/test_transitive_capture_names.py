## @package tests.test_transitive_capture_names
#  Relay lexical closure cells without borrowing descendant-local or global names.
import ast

import pytest

from pcresolve.scope_facts import transitive_captured_names


@pytest.mark.parametrize(('source', 'expected'), [
    ('def outer():\n    def inner():\n        return data\n    return inner()', ('data',)),
    ('def outer(data):\n    def inner():\n        return data\n    return inner()', ()),
    ('def outer():\n    data = {}\n    def inner():\n        return data\n    return inner()', ()),
    ('def outer():\n    global data\n    def inner():\n        return data\n    return inner()', ()),
    ('def outer():\n    def inner():\n        global data\n        return data\n    return inner()', ()),
    ('def outer():\n    def inner():\n        nonlocal data\n        data = {}\n    return inner()', ('data',)),
])
def test_named_nested_scopes_relay_only_free_cells(source, expected):
    assert transitive_captured_names(ast.parse(source).body[0], ('data',)) == expected
