## @package tests.test_regression_local_return_element_context
#  Keep project-local returned elements tied to their exact call arguments.

from pathlib import Path

import pytest

from pcresolve import analyze_project


FIXTURE = Path(__file__).parent / 'fixtures' / 'local_return_element_context'


@pytest.fixture(scope='module')
def calls():
    return analyze_project(str(FIXTURE)).all_api_calls


@pytest.mark.parametrize(('expression', 'owner'), [
    ('array.reshape(1)', 'numpy'),
    ('series.mean()', 'pandas'),
    ('local.reshape(1)', 'local'),
    ('text.strip()', 'python'),
    ("invalid.append('x')", 'unknown'),
    ('relayed.reshape(1)', 'numpy'),
    ('method_value.reshape(1)', 'numpy'),
    ('ambiguous.reshape(1)', 'unknown'),
    ('cyclic.reshape(1)', 'unknown'),
    ('rebound.reshape(1)', 'local'),
    ('forwarded.reshape(1)', 'numpy'),
    ('defaulted.strip()', 'python'),
    ('spread.reshape(1)', 'unknown'),
    ('conflict.mean()', 'unknown'),
    ('generated.reshape(1)', 'numpy'),
])
def test_returned_element_uses_its_call_context(calls, expression, owner):
    matches = [call for call in calls if call.expression == expression]
    assert len(matches) == 1
    assert matches[0].top_library == owner
