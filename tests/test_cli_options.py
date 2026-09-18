## @package tests.test_cli_options
#  Regression coverage for CLI output selection, diagnostics, and limits.

import itertools
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcresolve import cli
from pcresolve.diagnostics import Diagnostic
from pcresolve.types import ProjectAnalysis


FIXTURE = Path(__file__).parent / 'fixtures' / 'cli_options'
BAD_FIXTURE = Path(__file__).parent / 'fixtures' / 'regression_parse_errors'
OUTPUT_MODES = [
    ['--json'], ['--json-summary'], ['--debug-dump'],
    ['--explain-library', 'json'], ['--explain-symbol', 'json'],
    ['--explain-call', 'loads'],
]


def invoke(path, *options):
    return subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'pcresolve', str(path), *options],
        capture_output=True, text=True, encoding='utf-8',
    )


@pytest.mark.parametrize('left, right', list(itertools.combinations(OUTPUT_MODES, 2)))
def test_conflicting_output_modes_are_errors(left, right):
    run = invoke(FIXTURE, *left, *right)
    assert run.returncode == 2
    assert run.stdout == ''
    assert 'error:' in run.stderr
    assert left[0] in run.stderr and right[0] in run.stderr
    assert 'Traceback' not in run.stderr


@pytest.mark.parametrize('alias', ['--json-full', '--json-stable'])
@pytest.mark.parametrize('mode', OUTPUT_MODES[1:])
def test_hidden_json_aliases_conflict_with_other_modes(alias, mode):
    run = invoke(FIXTURE, alias, *mode)
    assert run.returncode == 2
    assert run.stdout == ''
    assert mode[0] in run.stderr


def test_full_json_aliases_can_be_combined():
    original = invoke(FIXTURE, '--json')
    combined = invoke(FIXTURE, '--json', '--json-full', '--json-stable')
    assert combined.returncode == 0, combined.stderr
    assert json.loads(combined.stdout) == json.loads(original.stdout)


@pytest.mark.parametrize('mode', OUTPUT_MODES[:2])
@pytest.mark.parametrize('modifier', ['--quiet', '--verbose', '--usage-summary'])
def test_json_rejects_text_only_modifiers(mode, modifier):
    run = invoke(FIXTURE, *mode, modifier)
    assert run.returncode == 2
    assert run.stdout == ''
    assert modifier in run.stderr


@pytest.mark.parametrize('mode', OUTPUT_MODES[3:])
@pytest.mark.parametrize('modifier', ['--quiet', '--usage-summary'])
def test_explain_rejects_summary_only_modifiers(mode, modifier):
    run = invoke(FIXTURE, *mode, modifier)
    assert run.returncode == 2
    assert run.stdout == ''
    assert modifier in run.stderr


def test_debug_dump_rejects_quiet():
    run = invoke(FIXTURE, '--debug-dump', '--quiet')
    assert run.returncode == 2
    assert '--quiet' in run.stderr


@pytest.mark.parametrize('flag', ['--explain-library', '--explain-symbol', '--explain-call'])
@pytest.mark.parametrize('query', ['', '   '])
def test_empty_explain_queries_are_errors(flag, query):
    run = invoke(FIXTURE, flag, query)
    assert run.returncode == 2
    assert run.stdout == ''
    assert flag in run.stderr


@pytest.mark.parametrize('options', [[], ['--json-summary'], ['--explain-call', 'loads']])
def test_negative_top_is_an_error(options):
    run = invoke(FIXTURE, *options, '--top', '-1')
    assert run.returncode == 2
    assert run.stdout == ''
    assert '--top' in run.stderr


@pytest.mark.parametrize('top, expected', [
    ('1', ['json']), ('2', ['json', 'pathlib']),
    ('0', ['json', 'pathlib', 'requests']),
])
def test_usage_summary_honors_top_and_preserves_counts(top, expected):
    run = invoke(FIXTURE, '--quiet', '--usage-summary', '--top', top)
    assert run.returncode == 0, run.stderr
    displayed = [line for line in run.stdout.splitlines() if line in ('json', 'pathlib', 'requests')]
    assert displayed == expected
    assert '  files: 2' in run.stdout
    assert '  api calls: 2' in run.stdout


@pytest.mark.parametrize('options', [['--verbose'], ['--quiet', '--verbose']])
def test_verbose_does_not_duplicate_errors(options):
    run = invoke(BAD_FIXTURE, *options)
    assert run.returncode == 0, run.stderr
    assert run.stdout.count('[ERROR] SYNTAX_ERROR') == 1


@pytest.mark.parametrize('options, warnings', [
    ([], 1), (['--verbose'], 1), (['--quiet'], 0),
    (['--quiet', '--verbose'], 0),
    (['--debug-dump', '--verbose'], 1),
    (['--explain-call', 'loads', '--verbose'], 1),
])
def test_diagnostics_are_printed_once_and_quiet_filters_warnings(monkeypatch, capsys, options, warnings):
    result = ProjectAnalysis(
        project_root=str(FIXTURE), files=[], all_api_calls=[],
        stats={'parsed_modules': 1, 'skipped_modules': 1},
        diagnostics=[
            Diagnostic(code='FILE_READ_ERROR', message='unreadable file', severity='error'),
            Diagnostic(code='TRACE_CYCLE', message='cycle in a parsed file', severity='warning'),
        ],
    )
    monkeypatch.setattr(cli, 'analyze_project', lambda path: result)
    monkeypatch.setattr(sys, 'argv', ['pcresolve', str(FIXTURE), *options])
    cli.main()
    output = capsys.readouterr().out
    assert output.count('[ERROR] FILE_READ_ERROR') == 1
    assert output.count('[WARNING] TRACE_CYCLE') == warnings
    if '--verbose' in options:
        assert '1 file(s) skipped.' in output
        assert '2 file(s) skipped.' not in output


@pytest.mark.parametrize('mode', OUTPUT_MODES[:2])
def test_strict_json_stays_machine_readable(mode):
    run = invoke(BAD_FIXTURE, *mode, '--strict')
    assert run.returncode == 1
    assert any(d['severity'] == 'error' for d in json.loads(run.stdout)['diagnostics'])
