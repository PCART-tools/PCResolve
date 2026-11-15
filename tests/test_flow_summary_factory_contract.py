## @package tests.test_flow_summary_factory_contract
#  Recursive summaries are constructed through an explicit internal factory.

import ast
from pathlib import Path

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
