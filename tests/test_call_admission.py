import ast
from types import SimpleNamespace

import pytest

from pcresolve.flow.model.results import FunctionRef
from pcresolve.flow.transfer.call_admission import apply_summary_admission, decide_call_admission
from pcresolve.flow.transfer.call_expression import CallExpressionMixin
from pcresolve.flow.transfer._summary_support import _call_span


@pytest.mark.parametrize(('seen', 'in_class', 'class_budget', 'budget', 'expected'), [
    (True, True, 0, 0, (False, False, None)),
    (False, True, 0, 0, (False, False, 'class_return_budget')),
    (False, True, 2, 0, (True, False, 'budget_exceeded')),
    (False, False, 0, 0, (False, False, 'budget_exceeded')),
    (False, True, 2, 1, (True, True, None)),
    (False, False, 0, 1, (False, True, None)),
])
def test_call_admission_decision(seen, in_class, class_budget, budget, expected):
    result = decide_call_admission(already_evaluated=seen, in_class_return=in_class,
                                   class_remaining=class_budget, summary_remaining=budget)
    assert (result.charge_class, result.charge_summary, result.boundary) == expected


def test_real_call_entry_charges_class_before_summary_budget_exit():
    class Host(CallExpressionMixin):
        evaluated_calls = set()
        analyzer = SimpleNamespace(_class_return_stack=['active'], _fact_calls=2)
        remaining = 0
        result = SimpleNamespace(boundaries=[])
        ref = FunctionRef(module='example', qualname='f')

        def evidence(self, node):
            return ['location']

    host = Host()
    assert host.call_expression(ast.parse('f()').body[0].value, {}) == []
    assert host.analyzer._fact_calls == 1
    assert host.remaining == 0
    assert not host.evaluated_calls
    assert host.result.boundaries[0]['reason'] == 'budget_exceeded'


def test_summary_charge_occurs_once_and_preserves_other_locations():
    first_location = (1, 2, 1, 5, '')
    next_location = (3, 4, 3, 7, ':with_exit:0:1')
    locations = {first_location}
    first = decide_call_admission(already_evaluated=False, in_class_return=False,
                                  class_remaining=0, summary_remaining=4)
    assert apply_summary_admission(first, 4, locations, next_location) == 3
    assert locations == {first_location, next_location}
    repeated = decide_call_admission(already_evaluated=True, in_class_return=False,
                                     class_remaining=0, summary_remaining=3)
    assert apply_summary_admission(repeated, 3, locations, next_location) == 3
    assert locations == {first_location, next_location}


def test_implicit_protocol_suffix_distinguishes_same_source_location():
    explicit = ast.parse('f()').body[0].value
    implicit = ast.parse('f()').body[0].value
    implicit._flow_implicit_suffix = ':with_exit:0:1'
    explicit_location = _call_span(explicit)
    implicit_location = _call_span(implicit)
    assert explicit_location[:-1] == implicit_location[:-1]
    assert explicit_location[-1] == ''
    assert implicit_location[-1] == ':with_exit:0:1'
    evaluated = {explicit_location}
    decision = decide_call_admission(already_evaluated=implicit_location in evaluated,
                                     in_class_return=False, class_remaining=0,
                                     summary_remaining=2)
    assert apply_summary_admission(decision, 2, evaluated, implicit_location) == 1
    assert evaluated == {explicit_location, implicit_location}
