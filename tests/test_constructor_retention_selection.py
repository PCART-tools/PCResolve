## @package tests.test_constructor_retention_selection

import ast

import pytest

from pcresolve.flow.proofs.callables._constructor_retention_selection import (
    retention_facts_are_closed,
    select_retained_store_writes,
)


@pytest.mark.parametrize('writes,calls,namespace,lookup,dependencies,hashes', [
    ([(None, 'run', None, None)], {'run'}, set(), None, set(), {}),
    ([(None, 'descriptor', None, None)], set(), {'descriptor'}, None, set(), {}),
    ([(None, 'lookup', None, None)], set(), set(), 'lookup', set(), {}),
    ([], set(), set(), None, {'helper.py'}, {}),
])
def test_open_conflicts_reject_the_collected_fact_set(
        writes, calls, namespace, lookup, dependencies, hashes):
    assert not retention_facts_are_closed(
        writes, calls, namespace, lookup, dependencies, hashes)


def test_closed_fact_set_preserves_unrelated_writes_and_source_dependencies():
    writes = [(None, 'value', None, None)]

    assert retention_facts_are_closed(
        writes, set(), {'descriptor'}, None, {'helper.py'}, {'helper.py': 'sha256'})


def test_final_selection_keeps_only_unique_public_root_assignment_stores():
    root, parent = object(), object()
    statement = ast.parse('self.value = 1').body[0]
    destination = statement.targets[0]
    duplicate = ast.parse('self.duplicate = 2').body[0]
    inherited = ast.parse('self.inherited = 3').body[0]
    private = ast.parse('self.__hidden = 4').body[0]
    descriptor = ast.parse('self.property = 5').body[0]
    non_assignment = ast.parse('self.called = 6').body[0].targets[0]
    writes = [
        (root, 'value', destination, statement),
        (root, 'duplicate', duplicate.targets[0], duplicate),
        (root, 'duplicate', duplicate.targets[0], duplicate),
        (parent, 'inherited', inherited.targets[0], inherited),
        (root, '__hidden', private.targets[0], private),
        (root, 'property', descriptor.targets[0], descriptor),
        (root, 'called', non_assignment, ast.parse('self.called').body[0]),
    ]

    selected = select_retained_store_writes(writes, root, {'property'})

    assert selected == [(root, 'value', destination, statement)]
