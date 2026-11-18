## @package tests.test_run_ci_gate
#  Validation evidence records successful and failed commands faithfully.

import json
from pathlib import Path
import subprocess
import sys


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run_ci_gate.py'


def test_records_failure_exit_code_and_command(tmp_path):
    report = tmp_path / 'nested' / 'failure.json'
    command = [sys.executable, str(SCRIPT), '--report', str(report), '--',
               'python', '-c', 'raise SystemExit(7)']
    result = subprocess.run(command, check=False)
    evidence = json.loads(report.read_text(encoding='utf-8'))
    assert result.returncode == evidence['exit_code'] == 7
    assert evidence['command'][1:] == ['-c', 'raise SystemExit(7)']
    assert evidence['revision']


def test_records_missing_command(tmp_path):
    report = tmp_path / 'missing.json'
    result = subprocess.run([sys.executable, str(SCRIPT), '--report', str(report), '--',
                             str(tmp_path / 'no-such-program')], check=False)
    evidence = json.loads(report.read_text(encoding='utf-8'))
    assert result.returncode == evidence['exit_code'] == 127
    assert evidence['error']
