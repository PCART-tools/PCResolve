import ast
from pathlib import Path
from unittest.mock import patch

from pcresolve import FlowAnalyzer, FunctionRef

ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def test_evidence_matches_ast_unicode_and_multiline():
    source = (ROOT / 'evidence.py').read_text(encoding='utf-8')
    nodes = {(n.lineno, n.col_offset, n.end_lineno, n.end_col_offset): n
             for n in ast.walk(ast.parse(source)) if hasattr(n, 'end_lineno')}
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='evidence', qualname='unicode_source'))
    for flow in result.calls[0].return_flows + result.calls[0].parameter_flows:
        for evidence in flow['evidence']:
            location = tuple(evidence[k] for k in ('lineno', 'col_offset', 'end_lineno', 'end_col_offset'))
            assert evidence['source_text'] == ast.get_source_segment(source, nodes[location])


def test_evidence_does_not_rescan_whole_source_per_expression():
    with patch('ast.get_source_segment', side_effect=AssertionError('Whole-file rescan')):
        result = FlowAnalyzer(project_root=ROOT).analyze(
            FunctionRef(module='evidence', qualname='unicode_source'))
    assert result.calls[0].return_flows
