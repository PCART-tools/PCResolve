## @package tests.test_single_file_input
#  Regression tests for ownership analysis of an explicit Python file.

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pcresolve import ProjectAnalyzer, analyze_project
from pcresolve.module_mapper import ModuleMapper
from pcresolve.views import build_full_view


FIXTURE = Path(__file__).parent / 'fixtures' / 'single_file_input'


def _invoke(*args, cwd=None, stdin=None):
    return subprocess.run(
        [sys.executable, '-X', 'utf8', '-m', 'pcresolve', *map(str, args)],
        cwd=cwd, input=stdin, capture_output=True, text=True, encoding='utf-8',
    )


def _assert_selected_file(data):
    assert data['schema_version'] == '1.0'
    assert data['profile'] == 'full'
    assert data['project_root'] == '.'
    assert data['stats']['parsed_modules'] == 1
    assert data['stats']['total_modules'] == 1
    assert data['diagnostics'] == []
    assert [file['file_path'] for file in data['files']] == ['a.py']
    assert {call['func_name']: call['top_library'] for call in data['all_api_calls']} == {
        'json.loads': 'json', 'decode': 'local', 'print': 'python',
    }
    assert {call['file_path'] for call in data['all_api_calls']} == {'a.py'}
    assert {item['file_path'] for item in data['all_symbol_provenance']} == {'a.py'}
    assert 'pathlib' not in data['library_usage']


@pytest.mark.parametrize('relative', [False, True])
def test_cli_analyzes_only_selected_file(relative):
    path = 'a.py' if relative else FIXTURE / 'a.py'
    run = _invoke(path, '--json', cwd=FIXTURE if relative else None)
    assert run.returncode == 0, run.stderr
    _assert_selected_file(json.loads(run.stdout))


def test_stdin_accepts_file_path():
    run = _invoke('--stdin', '--json', stdin=str(FIXTURE / 'a.py') + '\n')
    assert run.returncode == 0, run.stderr
    _assert_selected_file(json.loads(run.stdout))


@pytest.mark.parametrize('options, expected', [
    ([], 'Files: 1 parsed, 0 skipped'),
    (['--json-summary'], '"parsed_modules": 1'),
    (['--explain-call', 'json.loads'], 'Matches: 1'),
])
def test_file_supports_ownership_output_modes(options, expected):
    run = _invoke(FIXTURE / 'a.py', *options)
    assert run.returncode == 0, run.stderr
    assert expected in run.stdout


@pytest.mark.parametrize('use_analyzer', [False, True])
def test_python_api_accepts_file_path(use_analyzer):
    path = FIXTURE / 'a.py'
    result = ProjectAnalyzer(path).analyze() if use_analyzer else analyze_project(path)
    assert Path(result.project_root) == FIXTURE.resolve()
    _assert_selected_file(build_full_view(result))


def test_mapper_indexes_only_selected_file():
    mapper = ModuleMapper(FIXTURE / 'a.py')
    assert mapper.scan_project() == [str((FIXTURE / 'a.py').resolve())]
    assert mapper.get_all_modules() == ['a']
    mapper.clear()
    mapper.scan_project()
    assert mapper.get_all_modules() == ['a']


@pytest.mark.parametrize('filename', ['a.py', 'a.pyi'])
def test_selected_source_ignores_broken_sibling(tmp_path, filename):
    source = tmp_path / filename
    source.write_text('import json\njson.loads("{}")\n', encoding='utf-8')
    (tmp_path / 'broken.py').write_text('def broken(:', encoding='utf-8')
    run = _invoke(source, '--strict', '--json')
    assert run.returncode == 0, run.stderr
    data = json.loads(run.stdout)
    assert data['stats']['total_modules'] == 1
    assert data['diagnostics'] == []
    assert [file['file_path'] for file in data['files']] == [filename]
    assert data['all_api_calls'][0]['top_library'] == 'json'


@pytest.mark.parametrize('filename, module', [
    ('__init__.py', 'pkg.sub'), ('a.py', 'pkg.sub.a'),
])
def test_file_retains_enclosing_package_name(tmp_path, filename, module):
    package = tmp_path / 'pkg'
    package.mkdir()
    (package / '__init__.py').write_text('', encoding='utf-8')
    subpackage = package / 'sub'
    subpackage.mkdir()
    (subpackage / '__init__.py').write_text('', encoding='utf-8')
    source = subpackage / filename
    source.write_text('import json\njson.loads("{}")\n', encoding='utf-8')
    run = _invoke(source, '--json')
    assert run.returncode == 0, run.stderr
    data = json.loads(run.stdout)
    assert data['stats']['total_modules'] == 1
    assert data['files'][0]['module_name'] == module
    assert data['files'][0]['file_path'] == 'pkg/sub/' + filename
    assert data['all_api_calls'][0]['top_library'] == 'json'


@pytest.mark.parametrize('strict', [False, True])
def test_selected_syntax_error_has_diagnostic(tmp_path, strict):
    source = tmp_path / 'broken.py'
    source.write_text('def broken(:', encoding='utf-8')
    options = ['--strict'] if strict else []
    run = _invoke(source, '--json', *options)
    assert run.returncode == (1 if strict else 0), run.stderr
    data = json.loads(run.stdout)
    assert data['stats']['total_modules'] == 1
    assert data['stats']['skipped_modules'] == 1
    assert data['diagnostics'][0]['code'] == 'SYNTAX_ERROR'
    assert data['diagnostics'][0]['file_path'] == 'broken.py'


@pytest.mark.parametrize('exists', [False, True])
def test_invalid_file_input_fails(tmp_path, exists):
    source = tmp_path / ('notes.txt' if exists else 'missing.py')
    if exists:
        source.write_text('not Python', encoding='utf-8')
    run = _invoke(source, '--json')
    assert run.returncode != 0
    assert not run.stdout
    assert 'error:' in run.stderr
    assert 'Traceback' not in run.stderr
