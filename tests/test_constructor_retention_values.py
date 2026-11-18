## @package tests.test_constructor_retention_values

import ast

import pytest

from pcresolve.flow.proofs.callables._constructor_retention_values import (
    known_receiver_condition,
    known_receiver_value,
)


UNKNOWN = object()
OWNER = object()
METHOD = ast.parse('def init(self): pass').body[0]


def value(node, locals_, receiver, receiver_values=None):
    return known_receiver_value(node, locals_, receiver, receiver_values or {}, UNKNOWN)


def condition(source, *, locals_=None, receiver_values=None, builtin='confirmed_builtin'):
    node = ast.parse(source, mode='eval').body
    calls = []

    def query(owner, method, name):
        calls.append((owner, method, name))
        return builtin

    result = known_receiver_condition(
        node, locals_ or {}, 'self', OWNER, METHOD, UNKNOWN,
        known_value=lambda item, values, receiver: known_receiver_value(
            item, values, receiver, receiver_values or {}, UNKNOWN),
        builtin_name_status=query)
    return result, calls


def test_known_value_resolves_only_literals_locals_and_named_receiver_attributes():
    assert value(ast.Constant(value=0), {}, 'self') == 0
    assert value(ast.Name(id='local'), {'local': 'known'}, 'self') == 'known'
    assert value(ast.Attribute(value=ast.Name(id='self'), attr='flag', ctx=ast.Load()),
                 {}, 'self', {'flag': False}) is False
    assert value(ast.Name(id='open'), {}, 'self') is UNKNOWN
    assert value(ast.Attribute(value=ast.Name(id='other'), attr='flag', ctx=ast.Load()),
                 {}, 'self', {'flag': True}) is UNKNOWN


@pytest.mark.parametrize(('source', 'expected'), [
    ('not False', True),
    ('len(empty)', False),
    ('len(full)', True),
    ('False and open_value', False),
    ('True or open_value', True),
    ('not open_value', UNKNOWN),
    ('self.flag is None', True),
    ('self.flag is not None', False),
])
def test_condition_evaluator_keeps_short_circuit_and_identity_semantics(
        source, expected):
    result, _ = condition(source, locals_={'empty': [], 'full': [1]},
                          receiver_values={'flag': None})

    if expected is UNKNOWN:
        assert result is UNKNOWN
    else:
        assert result is expected


def test_len_is_evaluated_only_when_the_builtin_binding_is_confirmed():
    result, calls = condition('len([])', builtin='shadowed')

    assert result is UNKNOWN
    assert calls == [(OWNER, METHOD, 'len')]


def test_unknown_len_operand_does_not_gain_a_branch_conclusion():
    result, calls = condition('len(open_value)')

    assert result is UNKNOWN
    assert calls == [(OWNER, METHOD, 'len')]
