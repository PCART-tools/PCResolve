## @package tests.test_check_comment_coverage
#  Test mechanical checks for module comment headers and baseline gating.
#  测试模块注释文件头与基线门槛的机械检查。

import importlib.util
import json
from pathlib import Path
import sys

import pytest


spec = importlib.util.spec_from_file_location(
    'check_comment_coverage', Path(__file__).resolve().parents[1] / 'scripts/check_comment_coverage.py'
)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


MODULE_HEADER = '## @package example\n#  Explain the module.\n#  说明模块。\n'


def finding(path, line, code, detail=''):
    return checker.Finding(checker.display_path(path), line, code, detail)


@pytest.mark.parametrize('header', [
    '## @package example.module\n#  Explain the module.\n#  说明模块。\n\nimport os\n',
    '#!/usr/bin/env python3\n# coding: utf-8\n## @package example\n'
    '#  Explain the module over\n#  multiple lines.\n#\n#  说明模块。\n\nimport os\n',
    '## @package example\n#  Explain the module.\n#  说明模块。\n',
])
def test_valid_module_headers(tmp_path, header):
    path = tmp_path / 'example.py'
    path.write_text(header, encoding='utf-8')
    assert checker.inspect_file(path) == []


@pytest.mark.parametrize('source', [
    '## @package\n#  Explain.\n#  说明。\n\nimport os\n',
    '## @package bad-name\n#  Explain.\n#  说明。\n\nimport os\n',
    'import os\n## @package example\n#  Explain.\n#  说明。\n',
    '## @package example\n#  说明。\n#  Explain.\n\nimport os\n',
    '## @package example\n#  Explain. 说明。\n\nimport os\n',
    '## @package example\n#  Explain.\n#  说明。\nimport os\n',
    '## @package example\n#  Explain.\n#  说明。\n\n"""Docstring."""\n',
])
def test_invalid_module_headers(tmp_path, source):
    path = tmp_path / 'example.py'
    path.write_text(source, encoding='utf-8')
    assert checker.inspect_file(path)


def test_definition_comments_do_not_complete_module_header(tmp_path):
    path = tmp_path / 'example.py'
    path.write_text(
        '## @package example\n#  Explain the module.\n'
        '## Explain the function.\n## 说明函数。\n'
        '#\n#  @return Nothing.\ndef example():\n    pass\n',
        encoding='utf-8',
    )
    findings = checker.inspect_file(path)
    assert any('missing separate Chinese module description' in item for item in findings)
    assert any('missing blank line after module header' in item for item in findings)


def test_blank_line_separates_module_and_definition_comments(tmp_path):
    path = tmp_path / 'example.py'
    path.write_text(
        '## @package example\n#  Explain the module.\n#  说明模块。\n\n'
        '## Explain the function.\n## 说明函数。\n'
        '#\n#  @return Nothing.\ndef example():\n    pass\n',
        encoding='utf-8',
    )
    assert checker.inspect_file(path) == []


def test_gap_counts_group_by_file_and_category(tmp_path):
    path = tmp_path / 'example.py'
    counts = checker.gap_counts([
        finding(path, 3, 'missing @param', 'x'),
        finding(path, 3, 'missing @param', 'y'),
        finding(path, 3, 'missing @return'),
    ])
    assert counts == {
        path.resolve().as_posix(): {'missing @param': 2, 'missing @return': 1},
    }


def test_compare_baseline_reports_new_and_resolved():
    current = {'a.py': {'missing @param': 2}, 'b.py': {'missing @return': 1}}
    baseline = {'a.py': {'missing @param': 1, 'missing @return': 1},
                'c.py': {'missing @param': 3}}
    new, resolved = checker.compare_baseline(current, baseline)
    assert new == [('a.py', 'missing @param', 1, 2),
                   ('b.py', 'missing @return', 0, 1)]
    assert resolved == [('a.py', 'missing @return', 1, 0),
                        ('c.py', 'missing @param', 3, 0)]


def test_baseline_round_trip(tmp_path, monkeypatch, capsys):
    source = tmp_path / 'example.py'
    source.write_text(MODULE_HEADER + '\n\ndef example(x):\n    return x\n', encoding='utf-8')
    baseline = tmp_path / 'baseline.json'
    argv = ['check_comment_coverage', str(source)]

    monkeypatch.setattr(sys, 'argv', argv + ['--update-baseline', str(baseline)])
    assert checker.main() == 0
    document = json.loads(baseline.read_text(encoding='utf-8'))
    assert document['checker'] == 'comment_coverage'
    counts = document['files'][checker.display_path(source).as_posix()]
    assert counts == {'missing @param': 1, 'missing @return': 1,
                      'missing Chinese Doxygen summary': 1,
                      'missing English Doxygen summary': 1}

    monkeypatch.setattr(sys, 'argv', argv + ['--baseline', str(baseline)])
    assert checker.main() == 0

    source.write_text(MODULE_HEADER + '\n\ndef example(x, y):\n    return x\n', encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', argv + ['--baseline', str(baseline)])
    assert checker.main() == 1
    assert 'missing @param: 1 -> 2 (new)' in capsys.readouterr().out
