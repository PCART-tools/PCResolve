## @package tests.test_public_package_layout
#  Verify the 1.0.8 package layout and compatibility with previous imports.
import importlib
from pathlib import Path
import subprocess
import sys

import pcresolve
import pytest
from pcresolve.runtime._legacy_imports import _PROOF_MOVES


PACKAGE = Path(pcresolve.__file__).parent


def test_package_root_contains_only_entry_points():
    files = {path.name for path in PACKAGE.iterdir() if path.is_file()}
    assert files == {'__init__.py', '__main__.py', 'cli.py'}


def test_flow_analyzer_is_a_small_entry_and_orchestration_module():
    analyzer = PACKAGE / 'flow' / 'analyzer.py'
    assert len(analyzer.read_text(encoding='utf-8').splitlines()) <= 1000


def test_flow_summary_is_composed_from_domain_transfer_components():
    transfer = PACKAGE / 'flow' / 'transfer'
    summary = transfer / 'summary.py'
    assert len(summary.read_text(encoding='utf-8').splitlines()) <= 100
    for component in ('values', 'class_effects', 'call_evidence', 'expressions',
                      'containers', 'effects', 'context_managers', 'statements'):
        path = transfer / ('summary_' + component + '.py')
        assert path.is_file(), component


def test_expression_and_call_dispatchers_keep_each_handler_below_200_lines():
    import ast
    for relative in ('flow/transfer/call_expression.py',
                     'flow/transfer/summary_expressions.py'):
        path = PACKAGE / relative
        tree = ast.parse(path.read_text(encoding='utf-8'))
        long_functions = [(node.name, node.end_lineno - node.lineno + 1)
                          for node in ast.walk(tree)
                          if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                          and node.end_lineno - node.lineno + 1 > 200]
        assert not long_functions, (path, long_functions)


def test_class_creation_proofs_use_bounded_methods_and_a_small_entry_point():
    import ast
    path = PACKAGE / 'flow' / 'proofs' / 'classes' / '_class_creation_calls.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    functions = [node for node in ast.walk(tree)
                 if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    long_functions = [(node.name, node.end_lineno - node.lineno + 1)
                      for node in functions
                      if node.end_lineno - node.lineno + 1 > 200]
    entry_points = [node for node in functions if node.name == 'creation_calls']
    assert not long_functions, (path, long_functions)
    assert len(entry_points) == 1
    assert entry_points[0].end_lineno - entry_points[0].lineno + 1 <= 20


def test_flow_proofs_are_grouped_below_the_package_root():
    proofs = PACKAGE / 'flow' / 'proofs'
    assert {path.name for path in proofs.glob('*.py')} == {'__init__.py'}
    for directory in proofs.rglob('*'):
        if directory.is_dir() and directory.name != '__pycache__':
            assert (directory / '__init__.py').is_file(), directory
            implementations = [path for path in directory.glob('*.py')
                               if path.name != '__init__.py']
            assert len(implementations) <= 15, (directory, len(implementations))


def test_public_exports_resolve_from_their_owned_packages():
    assert pcresolve.ProjectAnalyzer is importlib.import_module('pcresolve.ownership.analyzer').ProjectAnalyzer
    assert pcresolve.SingleFileAnalyzer is importlib.import_module('pcresolve.ownership.collect.single_file').SingleFileAnalyzer
    assert pcresolve.SourceSpan is importlib.import_module('pcresolve.facts.program_facts').SourceSpan
    assert pcresolve.AnalysisLimits is importlib.import_module('pcresolve.runtime.limits').AnalysisLimits
    assert pcresolve.FlowAnalyzer is importlib.import_module('pcresolve.flow').FlowAnalyzer


def test_ownership_package_import_does_not_load_value_flow():
    code = ("import sys, pcresolve; "
            "assert 'pcresolve.flow' not in sys.modules; "
            "assert not any(name.startswith('pcresolve.flow.proofs') for name in sys.modules)")
    subprocess.run([sys.executable, '-c', code], check=True)


@pytest.mark.parametrize('name', [
    'container_predicates', 'mapping_attribute_transfer', 'mapping_key_access',
    'mapping_remainders', 'mapping_return_transfer',
])
def test_container_proof_moves_keep_module_identity(name):
    old = importlib.import_module('pcresolve.flow.proofs.' + name)
    new = importlib.import_module('pcresolve.flow.proofs.containers.' + name)
    assert old is new


@pytest.mark.parametrize('name', [
    '_class_creation', '_class_creation_calls', '_class_decoration', '_class_deferred',
    '_class_definition', '_class_effect_attributes', '_class_function_reads',
    '_class_identity', '_class_literal_loops', '_class_metadata_read', '_class_name_binding',
    '_class_observer_input', '_class_partial', '_class_read_binding', '_class_type_tests',
])
def test_class_proof_moves_keep_module_identity(name):
    old = importlib.import_module('pcresolve.flow.proofs.' + name)
    new = importlib.import_module('pcresolve.flow.proofs.classes.' + name)
    assert old is new


@pytest.mark.parametrize(('name', 'package'), sorted(_PROOF_MOVES.items()))
def test_other_proof_moves_keep_module_identity(name, package):
    old = importlib.import_module('pcresolve.flow.proofs.' + name)
    new = importlib.import_module('pcresolve.flow.proofs.' + package + '.' + name)
    assert old is new


@pytest.mark.parametrize(('old_name', 'implementation'), [
    ('analysis_limits', 'runtime.limits'),
    ('cross_file', 'ownership.analyzer'),
    ('single_file', 'ownership.collect.single_file'),
    ('single_file_assignment', 'ownership.collect.single_file_assignment'),
    ('project_call_context', 'ownership.resolve.project_call_context'),
    ('types', 'ownership.types'),
    ('views', 'ownership.views'),
    ('source_snapshot', 'frontend.source_snapshot'),
    ('program_facts', 'facts.program_facts'),
    ('entry_alias', 'flow.proofs.entry_alias'),
])
def test_previous_module_imports_preserve_module_identity(old_name, implementation):
    legacy = importlib.import_module('pcresolve.' + old_name)
    assert legacy is importlib.import_module('pcresolve.' + implementation)
    assert getattr(pcresolve, old_name) is legacy
