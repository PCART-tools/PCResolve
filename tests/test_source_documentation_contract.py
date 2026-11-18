"""Structural checks for production-source documentation conventions."""

import ast
from pathlib import Path


SOURCE_ROOT = Path(__file__).parents[1] / 'src' / 'pcresolve'


def test_production_source_has_no_runtime_docstrings():
    violations = []
    for path in sorted(SOURCE_ROOT.rglob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        if ast.get_docstring(tree):
            violations.append('%s:module' % path.relative_to(SOURCE_ROOT))
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                if ast.get_docstring(node):
                    violations.append('%s:%d:%s' % (
                        path.relative_to(SOURCE_ROOT), node.lineno, node.name))

    assert not violations, 'Runtime docstrings remain:\n' + '\n'.join(violations)
