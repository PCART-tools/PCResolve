import ast
from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


ROOT = Path(__file__).parent / 'fixtures' / 'value_flow'


def run(qualname):
    return FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='call_identity', qualname=qualname))


def expected_calls(qualname):
    source = (ROOT / 'call_identity.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    name = qualname.rpartition('.')[2]
    function = next(node for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == name)
    return {(node.lineno, node.col_offset, node.end_lineno, node.end_col_offset,
             ast.unparse(node.func)) for node in ast.walk(function)
            if isinstance(node, ast.Call)}


def test_nested_call_ids_use_complete_source_ranges():
    result = run('nested')
    actual = {(call.lineno, call.col_offset, call.end_lineno, call.end_col_offset,
               call.callee_name) for call in result.calls}
    assert actual == expected_calls('nested')
    assert len({call.id for call in result.calls}) == 2


def test_super_outer_call_is_not_merged_with_inner_call():
    result = run('Child.via_super')
    actual = {(call.lineno, call.col_offset, call.end_lineno, call.end_col_offset,
               call.callee_name) for call in result.calls}
    assert actual == expected_calls('Child.via_super')
    assert len({call.id for call in result.calls}) == 2
    assert result.find_calls(callee_name='super().echo')
