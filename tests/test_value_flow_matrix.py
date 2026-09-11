import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('flow_matrix', ROOT / 'scripts/evaluate_value_flow_matrix.py')
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
CASES = RUNNER.load_cases()
GAPS = json.loads((ROOT / 'tests/value_flow_known_gaps.json').read_text(encoding='utf-8'))['gaps']
PARAMETERS = []
for _, case in CASES:
    for dimension, subject, _, _ in RUNNER._checks(case):
        check_id = case['id'] + '/' + dimension + '/' + subject
        marks = [pytest.mark.xfail(strict=True, reason=GAPS[check_id]['reason'])] if check_id in GAPS else []
        PARAMETERS.append(pytest.param(check_id, id=check_id, marks=marks))


@pytest.fixture(scope='module')
def observations():
    return {row['id']: row for project, case in CASES
            for row in RUNNER.evaluate_case(project, case)['checks']}


@pytest.mark.parametrize('check_id', PARAMETERS)
def test_semantic_matrix(check_id, observations):
    row = observations[check_id]
    assert row['outcome'] not in RUNNER.FAILURES, row


def test_known_gap_marks_cannot_hide_errors_or_new_failure_modes(observations):
    assert set(GAPS) <= set(observations)
    for check_id, gap in GAPS.items():
        actual = observations[check_id]['outcome']
        if actual in RUNNER.FAILURES:
            assert actual == gap['outcome'], (check_id, gap, observations[check_id])
        # A success for a known gap is caught by strict XPASS on its own check.


def test_no_duplicate_generated_check_ids(observations):
    assert len(PARAMETERS) == len(observations)
