import copy
import json
from pathlib import Path

import pytest

from pcresolve import FlowAnalyzer, FunctionRef


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'entry.py').write_text(
        'from helper import identity\ndef entry(value):\n    return identity(value)\n', encoding='utf-8')
    (tmp_path / 'helper.py').write_text('def identity(value):\n    return value\n', encoding='utf-8')
    return tmp_path


def selector():
    return FunctionRef(module='entry', qualname='entry')


@pytest.mark.parametrize('option', ['max_depth', 'max_functions', 'max_call_contexts'])
@pytest.mark.parametrize('value', [0, -1])
def test_nonpositive_analysis_budget_rejected(project, option, value):
    with pytest.raises(ValueError, match='positive'):
        FlowAnalyzer(project_root=project).analyze(selector(), **{option: value})


def test_explicit_sources_match_project_scan(project):
    a = FlowAnalyzer(project_root=project).analyze(selector(), max_depth=2)
    b = FlowAnalyzer(source_files=reversed(sorted(project.glob('*.py'))), import_roots=[project]).analyze(
        selector(), max_depth=2)
    assert a.to_dict() == b.to_dict()


def test_source_addition_invalidates_expand_but_preserves_old_snapshot(project):
    analyzer = FlowAnalyzer(source_files=[project / 'entry.py'], import_roots=[project])
    before = analyzer.analyze(selector())
    saved = before.to_dict()
    analyzer.add_files([project / 'helper.py'])
    with pytest.raises(ValueError, match='Sources changed'):
        analyzer.expand(before, before.calls[0].id)
    assert before.to_dict() == saved
    after = analyzer.analyze(selector(), max_depth=2)
    assert after.trace_parameter('value')['return_paths']


def test_source_edit_invalidates_expand(project):
    analyzer = FlowAnalyzer(project_root=project)
    result = analyzer.analyze(selector())
    (project / 'helper.py').write_text('def identity(value):\n    return None\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Sources changed'):
        analyzer.expand(result, result.calls[0].id)


def test_serialization_and_queries_do_not_mutate_snapshot(project):
    result = FlowAnalyzer(project_root=project).analyze(selector(), max_depth=2)
    original = copy.deepcopy(result.to_dict())
    view = result.to_dict()
    view['calls'].clear()
    description = result.describe_call_flow(result.calls[0].id)
    description['argument_sources'].clear()
    query = result.trace_parameter('value')
    query['return_paths'].clear()
    assert result.to_dict() == original
    assert result.trace_parameter('value')['return_paths']
    assert json.loads(json.dumps(result.to_dict())) == original


def test_ambiguous_entry_needs_definition_line(project):
    path = project / 'ambiguous.py'
    path.write_text('def entry(x):\n    return x\ndef entry(x):\n    return None\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=project)
    with pytest.raises(ValueError, match='exactly one'):
        analyzer.analyze(FunctionRef(module='ambiguous', qualname='entry'))
    first = analyzer.analyze(FunctionRef(module='ambiguous', qualname='entry', lineno=1))
    second = analyzer.analyze(FunctionRef(module='ambiguous', qualname='entry', lineno=3))
    assert first.trace_parameter('x')['return_paths']
    assert not second.trace_parameter('x')['return_paths']


def test_unknown_parameter_and_call_are_not_empty_success(project):
    result = FlowAnalyzer(project_root=project).analyze(selector())
    with pytest.raises(ValueError, match='Unknown entry parameter'):
        result.trace_parameter('missing')
    with pytest.raises(KeyError):
        result.describe_call_flow('missing')


def test_expand_snapshot_matches_fresh_analysis(project):
    analyzer = FlowAnalyzer(project_root=project)
    shallow = analyzer.analyze(selector())
    saved = shallow.to_dict()
    expanded = analyzer.expand(shallow, shallow.calls[0].id)
    direct = analyzer.analyze(selector(), max_depth=2)
    assert expanded.trace_parameter('value') == direct.trace_parameter('value')
    assert shallow.to_dict() == saved


def test_changed_trusted_contract_invalidates_expand(project):
    analyzer = FlowAnalyzer(project_root=project)
    result = analyzer.analyze(selector())
    analyzer.return_summaries['vendor.wrap'] = {
        'parameters': ['value'], 'returns': [{'parameter': 'value', 'relation': 'direct'}],
        'provenance': 'test-only contract'}
    with pytest.raises(ValueError, match='Sources changed'):
        analyzer.expand(result, result.calls[0].id)
