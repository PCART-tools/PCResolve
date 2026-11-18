## @package tests.test_class_deferred_state

from pcresolve.flow.proofs.classes.deferred._class_deferred_state import merge_deferred_branch_state


def test_branch_join_keeps_only_bindings_and_literals_shared_by_both_paths():
    shared = ('helper', object())
    left = {'same': shared, 'metadata': ('fresh', object(), {'token': 1}), 'left': ('helper', object())}
    right = {'same': shared, 'metadata': ('fresh', left['metadata'][1], {'token': 2}),
             'right': ('helper', object())}
    state = {'stale': ('fresh', object())}
    values = {'stale': 'old'}
    left_values = {'same': 'stable', 'left': 'left'}
    right_values = {'same': 'stable', 'left': 'different', 'right': 'right'}

    merge_deferred_branch_state(state, values, left, right, left_values, right_values)

    assert state['same'] == shared
    assert state['metadata'] == ('fresh', left['metadata'][1], None)
    assert state['left'] == ('uncertain', None)
    assert state['right'] == ('uncertain', None)
    assert values == {'same': 'stable'}


def test_branch_join_mutates_the_path_dictionaries_it_was_given():
    state = {'old': ('helper', object())}
    values = {'old': 'before'}

    merge_deferred_branch_state(
        state, values, {'new': ('helper', object())}, {'new': ('helper', object())},
        {'literal': 'same'}, {'literal': 'same'})

    assert set(state) == {'new'}
    assert values == {'literal': 'same'}
