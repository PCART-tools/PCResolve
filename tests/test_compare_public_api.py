## @package tests.test_compare_public_api
#  Verify the frozen pre-refactor API contract and legacy aliases.

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('api_comparison', ROOT / 'scripts/compare_public_api.py')
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def _baseline():
    return json.loads((ROOT / 'tests/baselines/architecture_1_0_8/api.json').read_text(encoding='utf-8'))


def test_actual_public_api_and_legacy_modules_match_pre_refactor():
    baseline = _baseline()
    assert len(baseline['exports']) == 19
    assert len(baseline['legacy_modules']) == 56
    assert RUNNER.compare(baseline, RUNNER.manifest()) == {}


def test_public_signature_changes_and_removed_legacy_paths_are_reported():
    baseline = _baseline()
    current = copy.deepcopy(RUNNER.manifest())
    current['exports']['ProjectAnalyzer']['signature'] = '(changed)'
    current['legacy_modules'].pop('single_file')
    differences = RUNNER.compare(baseline, current)
    assert 'ProjectAnalyzer' in differences['exports']['changed']
    assert 'single_file' in differences['legacy_modules']['missing']


def test_changed_legacy_target_is_reported():
    baseline = _baseline()
    current = copy.deepcopy(RUNNER.manifest())
    current['legacy_modules']['single_file'] = 'ownership.analyzer'
    assert 'single_file' in RUNNER.compare(baseline, current)['legacy_modules']['changed']


def test_unimportable_legacy_module_is_reported(monkeypatch):
    baseline = _baseline()
    current = RUNNER.manifest()
    original = RUNNER.importlib.import_module

    def fail_one(name):
        if name == 'pcresolve.single_file':
            raise ImportError('unavailable')
        return original(name)

    monkeypatch.setattr(RUNNER.importlib, 'import_module', fail_one)
    differences = RUNNER.compare(baseline, current)
    assert 'single_file' in differences['legacy_modules']['changed']
