## @package tests.test_class_deferred_expression

import ast

import pytest

from pcresolve.flow.proofs.classes.deferred._class_deferred_expression import (
    rewrite_deferred_expression,
)


def rewrite(source, bindings=None, *, status=True, native=True, namespace=None, charge=None):
    node = ast.parse(source, mode='eval').body
    queries = []
    charged = []

    def read_namespace(absent=None):
        queries.append(absent)
        if namespace is None:
            return None
        return {'attributes': [namespace]} if absent is None else {'absent': absent}

    def consume(helper):
        charged.append(helper.name)
        if charge is not None:
            charge(helper)

    result = rewrite_deferred_expression(
        node, bindings or {}, {}, 'cls',
        string_value=lambda item, values: (
            item.value if isinstance(item, ast.Constant) and type(item.value) is str else None),
        source_span=lambda item: {'lineno': item.lineno},
        builtin_name_status=lambda name: status,
        native_namespace=lambda: native,
        namespace_read=read_namespace,
        consume_helper_budget=consume)
    return node, result, queries, charged


def test_expression_component_inlines_an_exact_helper_call_without_mutating_source_ast():
    helper = ast.parse('def helper(value):\n    return value + 1\n').body[0]
    original = ast.dump(helper, include_attributes=True)
    node, (rewritten, queries, calls), _, charged = rewrite(
        'helper(value)', {'helper': ('helper', helper)})

    assert ast.unparse(node) == 'helper(value)'
    assert ast.unparse(rewritten) == '(lambda value: value + 1)(value)'
    assert queries == []
    assert calls[0]['effects'] == 'source_body_requires_validation'
    assert calls[0]['runtime_helper_executed'] is False
    assert charged == ['helper']
    assert ast.dump(helper, include_attributes=True) == original


def test_guarded_vars_membership_returns_a_namespace_premise_and_marker():
    _, (rewritten, queries, calls), reads, charged = rewrite(
        "'known' in vars(cls)", namespace='known')

    assert ast.unparse(rewritten) == '$native_class_namespace_membership'
    assert queries == [{'attributes': ['known'], 'lookup_evidence': {'lineno': 1}}]
    assert reads == [None]
    assert calls == []
    assert charged == []


@pytest.mark.parametrize('status,native', [(False, True), (True, False)])
def test_vars_membership_is_not_specialized_without_both_namespace_guards(status, native):
    _, (rewritten, queries, _), reads, _ = rewrite(
        "'known' in vars(cls)", status=status, native=native, namespace='known')

    assert ast.unparse(rewritten) == "'known' in vars(cls)"
    assert queries == []
    assert reads == []


def test_getattr_fallback_requires_literal_and_absence_fact():
    _, (rewritten, queries, _), reads, _ = rewrite(
        "getattr(cls, 'missing', None)", namespace='missing')

    assert ast.unparse(rewritten) == 'None'
    assert queries == [{'absent': 'missing', 'lookup_evidence': {'lineno': 1}}]
    assert reads == ['missing']


def test_helper_expansion_budget_failure_propagates_to_the_proof_owner():
    helper = ast.parse('def helper(value):\n    return value\n').body[0]

    def exhausted(_):
        raise ValueError('budget exhausted')

    with pytest.raises(ValueError, match='budget exhausted'):
        rewrite('helper(value)', {'helper': ('helper', helper)}, charge=exhausted)


def test_star_arguments_do_not_create_an_exact_helper_binding():
    helper = ast.parse('def helper(value):\n    return value\n').body[0]

    with pytest.raises(ValueError):
        rewrite('helper(*values)', {'helper': ('helper', helper)})
