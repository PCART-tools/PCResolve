import ast

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.scope_facts import FLOW_SCOPE, MAPPING_SCOPE, function_scope_facts


def test_lexical_fact_collection_does_not_use_python_expression_recursion():
    node = ast.parse('def entry(a, **kw): return external').body[0]
    expression = ast.Name(id='external', ctx=ast.Load())
    for _ in range(2500):
        expression = ast.BinOp(left=expression, op=ast.Add(),
                               right=ast.Name(id='a', ctx=ast.Load()))
    node.body[0].value = expression
    for policy in (FLOW_SCOPE, MAPPING_SCOPE):
        facts = function_scope_facts(node, policy)
        assert facts.loaded == frozenset(('external', 'a'))
        assert facts.bound == (frozenset(('a', 'kw')) if policy.include_parameters else frozenset())


def test_unrelated_deep_function_does_not_crash_a_constructor_query(tmp_path):
    source = ('class Holder:\n    pass\n'
              'def noise(x):\n    return ' + '+'.join(['x'] * 450) + '\n'
              'def entry(**kw):\n    return Holder()\n')
    (tmp_path / 'cases.py').write_text(source)
    result = FlowAnalyzer(project_root=tmp_path).analyze(FunctionRef('cases', 'entry'))
    assert result.entry.qualname == 'entry'
    assert any(call.callee_name == 'Holder' for call in result.calls)
