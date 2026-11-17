## @package tests.test_class_deferred_metadata

import ast
import copy

from pcresolve.flow.proofs.classes.deferred._class_deferred_metadata import (
    store_metadata_member,
    update_metadata_write,
)


def formation():
    return {'metadata_shapes': {'documentation': ['str'], 'name': ['str'], 'qualname': ['str']},
            'metadata_writes': []}


def span(node):
    return {'lineno': node.lineno}


def string_value(node, values):
    if isinstance(node, ast.Name):
        return values.get(node.id)
    return node.value if isinstance(node, ast.Constant) and type(node.value) is str else None


def test_store_metadata_records_a_copy_and_marks_the_proof_token_published():
    original = formation()
    state = {'function': ('fresh', object(), {'token': 8, 'formation': original})}
    generated, published = [], set()

    store_metadata_member('PublicMethod', 'function', state, ast.parse('cls.x = function').body[0],
                          generated, published, span)

    assert generated[0]['attribute'] == 'PublicMethod'
    assert generated[0]['metadata_formation'] == original
    assert generated[0]['metadata_formation'] is not original
    assert generated[0]['_token'] == 8
    assert published == {8}


def test_later_alias_write_updates_metadata_and_invalidates_published_snapshot():
    function = object()
    payload = {'token': 3, 'formation': formation()}
    state = {'left': ('fresh', function, payload), 'right': ('fresh', function, payload)}
    generated = [{'attribute': 'Alias', 'metadata_formation': copy.deepcopy(payload['formation']),
                  'store_evidence': {}, '_token': 3}]
    published = {3}
    token_nodes = {3: function}
    assignment = ast.parse("left.__name__ = 'updated'").body[0]

    update_metadata_write('left', '__name__', assignment.value, state, {},
                          assignment, generated, published, token_nodes, span, string_value)

    assert generated == []
    assert state['left'][2]['formation']['metadata_shapes']['name'] == ['str']
    assert state['right'][2] is state['left'][2]
    assert state['left'][2]['formation']['metadata_writes'] == [{'lineno': 1}]


def test_unknown_joined_payload_invalidates_only_the_possibly_aliased_snapshot():
    first, second = object(), object()
    state = {'left': ('fresh', first, None)}
    generated = [
        {'attribute': 'First', '_token': 1},
        {'attribute': 'Second', '_token': 2},
    ]

    update_metadata_write('left', '__doc__', ast.Constant(value=None), state, {},
                          ast.parse('left.__doc__ = None').body[0], generated, set(),
                          {1: first, 2: second}, span, string_value)

    assert generated == [{'attribute': 'Second', '_token': 2}]
