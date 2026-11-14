## @package tests.test_verify_architecture_inputs
#  Preflight must reject missing and incomplete frozen baselines.

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('architecture_preflight', ROOT / 'scripts/verify_architecture_inputs.py')
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)


def test_committed_baseline_inventory_is_complete():
    assert len(RUNNER.check_baselines()['exports']) == 19


def test_missing_baseline_fails_before_imports(tmp_path):
    with pytest.raises(FileNotFoundError):
        RUNNER.check_baselines(tmp_path)


def test_incomplete_baseline_is_rejected(tmp_path):
    for name in ('analysis.json', 'api.json'):
        record = json.loads((RUNNER.BASELINES / name).read_text(encoding='utf-8'))
        if name == 'analysis.json':
            record['outputs'].pop(next(iter(record['outputs'])))
        (tmp_path / name).write_text(json.dumps(record), encoding='utf-8')
    with pytest.raises(ValueError, match='Incomplete analysis baseline'):
        RUNNER.check_baselines(tmp_path)


def test_syntax_error_fails_preflight_before_public_imports(tmp_path, monkeypatch):
    source = tmp_path / 'src' / 'pcresolve' / 'broken.py'
    source.parent.mkdir(parents=True)
    source.write_text('def broken(:\n', encoding='utf-8')
    monkeypatch.setattr(RUNNER, 'ROOT', tmp_path)
    monkeypatch.setattr(RUNNER, 'check_baselines', lambda: {})
    with pytest.raises(RuntimeError, match='Source compilation failed'):
        RUNNER.main()
