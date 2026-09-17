## @package tests.test_scope_facts
#  Shared lexical facts preserve the existing consumers' scope policies.

import ast
from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef
from pcresolve.mapping_facts import bound_names
from pcresolve.scope_facts import (FLOW_SCOPE, MAPPING_SCOPE,
                                   function_scope_facts,
                                   statement_scope_facts)


ROOT = Path(__file__).parent / 'fixtures' / 'scope_facts'


SOURCE = '''
def wrapper():
    outer_name = None
    def sample(parameter):
        global global_name
        nonlocal outer_name
        global_name = parameter
        outer_name = parameter
        import package.module
        from package import value as alias
        try:
            local = data
        except Exception as error:
            local = error
        values = [item for item in data if (leaked := item)]
        callback = lambda: outer_name
        def inner():
            return ignored
        return callback
'''


def _sample():
    wrapper = ast.parse(SOURCE).body[0]
    return next(node for node in wrapper.body
                if isinstance(node, ast.FunctionDef) and node.name == 'sample')


def test_flow_scope_profile_retains_current_loaded_and_bound_names():
    facts = function_scope_facts(_sample(), FLOW_SCOPE)
    assert facts.globals == frozenset(['global_name'])
    assert facts.nonlocals == frozenset(['outer_name'])
    assert facts.bound == frozenset([
        'parameter', 'global_name', 'outer_name', 'package', 'alias',
        'local', 'item', 'leaked', 'values', 'callback', 'inner'])
    assert {'parameter', 'data', 'error', 'item', 'outer_name', 'callback'} <= facts.loaded
    # Nested named scopes stop collection; lambda bodies retain Flow's existing
    # compatibility behavior and therefore contribute outer_name.
    assert 'ignored' not in facts.loaded


def test_mapping_profile_excludes_outer_declarations_and_comprehension_locals():
    sample = _sample()
    facts = statement_scope_facts(sample.body, MAPPING_SCOPE)
    assert facts.bound == frozenset([
        'package', 'alias', 'local', 'error', 'leaked', 'values',
        'callback', 'inner'])
    assert 'global_name' not in facts.bound and 'outer_name' not in facts.bound
    assert 'item' not in facts.bound
    assert bound_names(sample.body) == set(facts.bound)


def test_scope_facts_are_immutable_and_repeatable():
    node = _sample()
    first = function_scope_facts(node, FLOW_SCOPE)
    second = function_scope_facts(node, FLOW_SCOPE)
    assert first == second
    assert isinstance(first.loaded, frozenset) and isinstance(first.bound, frozenset)


def test_flow_uses_shared_capture_facts_for_nonlocal_and_nested_lambda_names():
    result = FlowAnalyzer(project_root=ROOT).analyze(
        FunctionRef(module='main', qualname='outer'), max_depth=2)
    call = result.find_calls(callee_name='child')[0]
    assert [binding['capture'] for binding in call.capture_bindings] == [
        'captured', 'second']
    assert [binding['sources'][0]['source'] for binding in call.capture_bindings] == [
        'first', 'second']


def test_flow_rebuilds_scope_facts_after_source_change(tmp_path):
    path = tmp_path / 'main.py'
    path.write_text(
        'def outer(x, y):\n'
        '    def inner(): return x\n'
        '    return inner()\n', encoding='utf-8')
    analyzer = FlowAnalyzer(project_root=tmp_path)
    first = analyzer.analyze(FunctionRef(module='main', qualname='outer'), max_depth=2)
    assert first.find_calls(callee_name='inner')[0].capture_bindings[0]['capture'] == 'x'
    path.write_text(
        'def outer(x, y):\n'
        '    def inner(): return y\n'
        '    return inner()\n', encoding='utf-8')
    second = analyzer.analyze(FunctionRef(module='main', qualname='outer'), max_depth=2)
    assert second.find_calls(callee_name='inner')[0].capture_bindings[0]['capture'] == 'y'
