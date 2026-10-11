## @package tests.test_incremental_flow_facts
#  Source edits rebuild only their file facts and still equal a fresh query.

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


@pytest.mark.parametrize('change', ['edit', 'syntax', 'delete', 'roots'])
def test_changed_file_reuses_unaffected_index_facts(tmp_path, monkeypatch, change):
    main = tmp_path / 'main.py'
    helper = tmp_path / 'helper.py'
    main.write_text('from helper import identity\ndef entry(value): return identity(value)\n', encoding='utf-8')
    helper.write_text('def identity(value): return value\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    entry = FunctionRef(module='main', qualname='entry')
    old = analyzer.analyze(entry, max_depth=2).to_dict()
    visited = []
    original = analyzer._collect_file_index
    def record(path, document, module):
        visited.append(path)
        return original(path, document, module)
    monkeypatch.setattr(analyzer, '_collect_file_index', record)
    if change == 'edit':
        helper.write_text('def identity(value): return False\n', encoding='utf-8')
    elif change == 'syntax':
        helper.write_text('def broken(:\n', encoding='utf-8')
    elif change == 'delete':
        helper.unlink()
    else:
        analyzer.roots = [str(tmp_path.parent)]
        entry = FunctionRef(module=tmp_path.name + '.main', qualname='entry')
    current = analyzer.analyze(entry, max_depth=2).to_dict()
    fresh = FlowAnalyzer(source_files=analyzer.files, import_roots=analyzer.roots)
    assert current == fresh.analyze(entry, max_depth=2).to_dict()
    assert old != current
    assert str(main) not in visited if change != 'roots' else str(main) in visited
    assert len(visited) == (1 if change == 'edit' else 2 if change == 'roots' else 0)
