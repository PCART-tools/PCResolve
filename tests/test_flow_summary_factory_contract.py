## @package tests.test_flow_summary_factory_contract
#  Recursive summaries are constructed through an explicit internal factory.

import ast
from pathlib import Path

from pcresolve.flow.model.results import FlowAnalysis, FunctionRef
from pcresolve.flow.transfer import summary, summary_context_managers, summary_values


def _tree(module):
    return ast.parse(Path(module.__file__).read_text(encoding='utf-8'))


def test_summary_composition_does_not_inject_classes_into_imported_modules():
    tree = _tree(summary)
    forbidden = [node for node in ast.walk(tree)
                 if isinstance(node, ast.Attribute)
                 and isinstance(node.value, ast.Name)
                 and node.value.id == 'sys' and node.attr == 'modules']
    injected = [node for node in ast.walk(tree)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == 'setattr']
    assert not forbidden
    assert not injected


def test_recursive_summary_sites_use_the_composed_summary_factory():
    for module in (summary_values, summary_context_managers):
        tree = _tree(module)
        factory_calls = [node for node in ast.walk(tree)
                         if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute)
                         and node.func.attr == '_make_child_summary']
        direct_class_references = [node for node in ast.walk(tree)
                                   if isinstance(node, ast.Name)
                                   and node.id == '_Summary']
        assert factory_calls
        assert not direct_class_references

    assert hasattr(summary._Summary, '_make_child_summary')


def test_transfer_modules_use_explicit_imports():
    transfer_dir = Path(summary.__file__).parent
    wildcard_imports = []
    for path in transfer_dir.glob('*.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        wildcard_imports.extend(
            (path.name, node.lineno)
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and any(alias.name == '*' for alias in node.names)
        )

    assert wildcard_imports == []


def test_child_summary_factory_isolates_query_state():
    class Analyzer:
        texts = {'sample.py': 'def f():\n    return 1\n'}

    analyzer = Analyzer()
    ref = FunctionRef(module='sample', qualname='f', file_path='sample.py', lineno=1)
    result = FlowAnalysis(entry=ref, inputs={})
    node = ast.parse(analyzer.texts['sample.py']).body[0]

    parent = summary._Summary(analyzer, result, ref, node, remaining=4)
    child_result = FlowAnalysis(entry=ref, inputs={})
    child = parent._make_child_summary(child_result, ref, node, remaining=2)

    assert child.analyzer is analyzer
    assert child.result is child_result
    assert child.remaining == 2
    assert child.calls is not parent.calls
    assert child.evaluated_calls is not parent.evaluated_calls
    assert child.conditions is not parent.conditions

    parent.calls.append(object())
    parent.evaluated_calls.add((1,))
    assert child.calls == []
    assert child.evaluated_calls == set()
