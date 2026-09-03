## @package tests.test_mapping_facts
#  Mapping selections are private call-edge facts, not return-owner guesses.

import ast

from pcresolve.call_graph import FunctionId
from pcresolve.mapping_facts import MappingFacts, bound_names
from pcresolve.scope import Binding


def _facts():
    bindings = {}
    facts = MappingFacts(bindings.get,
                         lambda node: FunctionId('example', '<lambda>'),
                         bindings.get)
    bindings['consume'] = Binding('consume', 'local')
    bindings['consume'].mapping_value = facts.callable(FunctionId('example', 'consume'))
    bindings['other'] = Binding('other', 'local')
    bindings['other'].mapping_value = facts.callable(FunctionId('example', 'other'))
    return facts, bindings


def _value(facts, expression):
    return facts.value(ast.parse(expression, mode='eval').body)


def test_duplicate_python_keys_and_exact_default_selection():
    facts, _ = _facts()
    selected = _value(facts, "{True: consume, 1: other}[True]")
    assert selected.targets() == ((FunctionId('example', 'other'),), True)
    selected = _value(facts, "{}.get('missing', consume)")
    assert selected.targets() == ((FunctionId('example', 'consume'),), True)


def test_unknown_key_keeps_candidates_but_not_exact_return_context():
    facts, _ = _facts()
    selected = _value(facts, "{'run': consume}.get(key)")
    assert selected.targets() == ((FunctionId('example', 'consume'),), False)


def test_external_alternative_does_not_become_an_exact_local_target():
    facts, _ = _facts()
    selected = _value(facts, "{'run': consume}.get(key, external)")
    assert selected.targets() == ((FunctionId('example', 'consume'),), False)


def test_mutation_invalidates_already_captured_selection():
    facts, bindings = _facts()
    table = _value(facts, "{'module': {'run': consume}}")
    bindings['table'] = Binding('table', 'local', mapping_value=table)
    captured = _value(facts, "table['module']['run']")
    assert captured.targets()[1]
    facts.invalidate(_value(facts, "table['module']"))
    assert captured.targets() == ((), False)


def test_bound_names_exclude_nested_scopes_and_outer_declarations():
    body = ast.parse('''
global registry
registry = {}
local = {}
def inner():
    unrelated = {}
items = [item for item in data]
''').body
    assert bound_names(body) == {'local', 'inner', 'items'}
