import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'
MATRIX_CONTAINERS = Path(__file__).parent / 'fixtures' / 'value_flow_matrix' / 'containers'


def invoke(*args):
    return subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pcresolve', *map(str, args)],
                          capture_output=True, text=True, encoding='utf-8')


def test_project_flow_json_and_depth():
    run = invoke(ROOT, '--value-flow', '--entry', 'main:deep', '--depth', 3, '--json')
    assert run.returncode == 0, run.stderr
    result = json.loads(run.stdout)
    assert result['schema_version'] == 'flow-0.2'
    assert len(result['functions']) == 3
    assert 'all_api_calls' not in result


def test_explicit_sources_and_output_file(tmp_path):
    output = tmp_path / 'result.json'
    run = invoke('--value-flow', '--entry', 'main:entry',
                 '--source-file', ROOT / 'main.py', '--source-file', ROOT / 'helper.py',
                 '--import-root', ROOT, '--json', '--output', output)
    assert run.returncode == 0, run.stderr
    assert not run.stdout
    result = json.loads(output.read_text(encoding='utf-8'))
    assert len(result['inputs']['source_files']) == 2
    assert result['calls'][0]['target']['module'] == 'helper'


def test_flow_text_has_flows_and_boundaries():
    run = invoke(ROOT, '--value-flow', '--entry', 'main:entry')
    assert run.returncode == 0, run.stderr
    assert 'Parameter flows' in run.stdout
    assert 'Return flows' in run.stdout
    assert 'depth_limit' in run.stdout


def test_flow_text_includes_supported_effects():
    run = invoke(MATRIX_CONTAINERS, '--value-flow', '--entry',
                 'cases:cross_call_clear', '--depth', 2)
    assert run.returncode == 0, run.stderr
    assert 'Effects: container_clear' in run.stdout


@pytest.mark.parametrize('options', [
    ['--value-flow'],
    ['--value-flow', '--entry', 'bad'],
    ['--value-flow', '--entry', 'main:entry', '--depth', '0'],
    ['--value-flow', '--entry', 'main:entry', '--json-summary'],
    ['--entry', 'main:entry'],
    ['--value-flow', '--entry', 'main:missing'],
])
def test_invalid_flow_options_are_cli_errors(options):
    run = invoke(ROOT, *options)
    assert run.returncode == 2
    assert 'error:' in run.stderr
    assert 'Traceback' not in run.stderr


def test_missing_explicit_file_is_error():
    run = invoke('--value-flow', '--entry', 'main:entry', '--source-file', ROOT / 'missing.py')
    assert run.returncode == 2


def test_budget_is_forwarded():
    run = invoke(ROOT, '--value-flow', '--entry', 'main:deep', '--depth', 3,
                 '--max-functions', 1, '--max-call-contexts', 1, '--json')
    assert run.returncode == 0, run.stderr
    assert any(b['reason'] == 'budget_exceeded' for b in json.loads(run.stdout)['boundaries'])


def test_existing_ownership_json_still_works():
    run = invoke(ROOT, '--json')
    assert run.returncode == 0, run.stderr
    assert 'all_api_calls' in json.loads(run.stdout)
