## @package tests.test_compare_analysis_baseline
#  Baseline comparisons detect changes without replacing their reference input.

import importlib.util
import json
from pathlib import Path
import sys

import pytest


@pytest.fixture
def runner(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / 'scripts'
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location('analysis_baseline', scripts / 'compare_analysis_baseline.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv('PYTHONHASHSEED', '0')
    return module


def _report(digest='same', seconds=1):
    return {'python': '3.13.9', 'hash_seed': '0', 'outputs': {'ownership/sample': digest},
            'call_counts': {'ownership/sample': 2}, 'seconds': {'ownership/sample': seconds}}


@pytest.mark.parametrize('digest, seconds, exit_code', [
    ('same', 9, 0), ('changed', 1, 1)])
def test_compare_public_outputs_but_ignore_timing(runner, monkeypatch, tmp_path, digest, seconds, exit_code):
    before, after = tmp_path / 'before.json', tmp_path / 'after.json'
    before.write_text(json.dumps(_report()), encoding='utf-8')
    monkeypatch.setattr(runner, 'capture_baseline', lambda: _report(digest, seconds))
    monkeypatch.setattr(sys, 'argv', ['baseline', '--output', str(after), '--compare', str(before)])
    assert runner.main() == exit_code
    assert json.loads(before.read_text(encoding='utf-8')) == _report()
    assert json.loads(after.read_text(encoding='utf-8')) == _report(digest, seconds)


def test_compare_detects_call_inventory_change(runner, monkeypatch, tmp_path):
    before = tmp_path / 'before.json'
    before.write_text(json.dumps(_report()), encoding='utf-8')
    current = _report()
    current['call_counts']['ownership/sample'] = 3
    monkeypatch.setattr(runner, 'capture_baseline', lambda: current)
    monkeypatch.setattr(sys, 'argv', ['baseline', '--output', str(tmp_path / 'after.json'),
                                    '--compare', str(before)])
    assert runner.main() == 1


def test_baseline_cannot_overwrite_its_comparison_reference(runner, monkeypatch, tmp_path):
    before = tmp_path / 'before.json'
    original = json.dumps(_report())
    before.write_text(original, encoding='utf-8')
    monkeypatch.setattr(runner, 'capture_baseline', lambda: _report('changed'))
    monkeypatch.setattr(sys, 'argv', ['baseline', '--output', str(before), '--compare', str(before)])
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 2
    assert before.read_text(encoding='utf-8') == original


def test_incompatible_baseline_is_rejected_without_writing_output(runner, monkeypatch, tmp_path):
    before, after = tmp_path / 'before.json', tmp_path / 'after.json'
    previous = _report()
    previous['hash_seed'] = None
    before.write_text(json.dumps(previous), encoding='utf-8')
    monkeypatch.setattr(runner, 'capture_baseline', lambda: _report())
    monkeypatch.setattr(sys, 'argv', ['baseline', '--output', str(after), '--compare', str(before)])
    with pytest.raises(SystemExit) as error:
        runner.main()
    assert error.value.code == 2
    assert not after.exists()


def test_missing_corpus_is_rejected_before_analysis(runner, monkeypatch, tmp_path):
    manifest = tmp_path / 'ground_truth' / 'projects.json'
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({'projects': {'missing': {'path': 'absent'}}}), encoding='utf-8')
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    monkeypatch.setattr(runner, 'load_cases', lambda: [])
    with pytest.raises(ValueError, match='ownership corpus'):
        runner.capture_baseline()


def test_missing_explicit_flow_source_is_rejected(runner, tmp_path):
    with pytest.raises(ValueError, match='flow source'):
        runner.validate_inputs(tmp_path, {}, [(tmp_path, {'id': 'case', 'files': ['missing.py']})],
                               expected_ownership=0, expected_flow=1)


def test_incomplete_corpus_inventory_is_rejected(runner, tmp_path):
    with pytest.raises(ValueError, match='inventory'):
        runner.validate_inputs(tmp_path, {}, [], expected_ownership=42, expected_flow=83)


def test_flow_path_canonicalization_preserves_semantics_and_external_paths(runner):
    one = {'file_path': 'C:\\work\\one\\src\\a.py',
           'source_files': ['C:\\work\\one\\src\\a.py'],
           'id': 'C:\\work\\one\\src\\a.py:1:2:3:4',
           'output_container': '$heap:C:\\work\\one\\src\\a.py:2:3',
           'expression': 'C:\\work\\one\\src\\a.py',
           'evidence': [{'file_path': 'C:\\external\\a.py'}],
           'sha256': {'C:\\work\\one\\src\\a.py': 'abc'},
           'boundary': 'unknown'}
    two = {'file_path': '/tmp/two/src/a.py', 'source_files': ['/tmp/two/src/a.py'],
           'id': '/tmp/two/src/a.py:1:2:3:4',
           'output_container': '$heap:/tmp/two/src/a.py:2:3',
           'expression': 'C:\\work\\one\\src\\a.py',
           'evidence': [{'file_path': 'C:\\external\\a.py'}],
           'sha256': {'/tmp/two/src/a.py': 'abc'},
           'boundary': 'unknown'}
    first = runner._canonicalize_paths(one, 'C:\\work\\one')
    second = runner._canonicalize_paths(two, '/tmp/two')
    assert first == second
    assert first['id'] == '$ROOT/src/a.py:1:2:3:4'
    assert first['output_container'] == '$heap:$ROOT/src/a.py:2:3'
    assert first['expression'] == one['expression']
    assert first['evidence'] == one['evidence']
    assert first['sha256'] == {'$ROOT/src/a.py': 'abc'}
    assert runner._fingerprint(first) != runner._fingerprint({**first, 'boundary': 'resolved'})


def test_canonicalization_rejects_colliding_path_keys(runner):
    value = {'sha256': {'C:\\work\\src\\a.py': 'first',
                        '$ROOT/src/a.py': 'second'}}
    with pytest.raises(ValueError, match='duplicate key'):
        runner._canonicalize_paths(value, 'C:\\work')
