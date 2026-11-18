## @package tests.test_flow_environment_transfer
#  Branch joins retain uncertainty without mutating their inputs.
from pcresolve.flow.transfer.environment import merge_environments, merge_result_sources


def test_missing_branch_keeps_import_uncertain():
    source = {'kind': 'import', 'name': 'json'}
    assert merge_environments([{'x': [source]}, {}]) == {
        'x': [{'kind': 'import', 'name': 'json', 'import_incomplete': True}]}
    assert source == {'kind': 'import', 'name': 'json'}


def test_container_result_remains_incomplete_with_missing_branch():
    source = {'kind': 'container', 'container_object': True}
    assert merge_result_sources([source], []) == [dict(source, value_incomplete=True)]
    assert 'value_incomplete' not in source
