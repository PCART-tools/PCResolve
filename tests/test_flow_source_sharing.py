## @package tests.test_flow_source_sharing
#  Source lines and span evidence are shared per source generation.

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.flow.model.results import FlowAnalysis
from pcresolve.flow.transfer.summary import _Summary


SOURCE = (
    'def helper(value):\n'
    '    return value\n'
    '\n'
    '\n'
    'def entry(value):\n'
    '    return helper(value)\n'
)


def test_source_lines_and_evidence_are_shared_per_generation(tmp_path):
    (tmp_path / 'main.py').write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index(preserve_source_facts=True)
    path = str(tmp_path / 'main.py')
    lines = analyzer._source_lines(path)
    assert analyzer._source_lines(path) is lines
    analyzer._index(preserve_source_facts=True)
    assert analyzer._source_lines(path) is lines


def test_summary_uses_the_generation_evidence_cache(tmp_path):
    (tmp_path / 'main.py').write_text(SOURCE, encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    analyzer._index(preserve_source_facts=True)
    ref, node = next(pair for pair in analyzer.definitions if pair[0].qualname == 'entry')
    summary = _Summary(analyzer, FlowAnalysis(ref, {}), ref, node, 10)
    assert summary.evidence_cache is analyzer._source_evidence_cache
    assert summary.evidence(node) is summary.evidence(node)
    assert summary.source_lines is analyzer._source_lines(ref.file_path)
