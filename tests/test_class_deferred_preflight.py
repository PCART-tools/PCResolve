## @package tests.test_class_deferred_preflight
#  Bound class-deferred proof inputs before interpreting declaration effects.

import ast

import pytest

from pcresolve.flow.proofs.classes._class_deferred import _within_function_budget
from pcresolve.runtime.limits import AnalysisBudget, AnalysisLimitExceeded, AnalysisLimits


class Analyzer:
    def __init__(self, budget=None):
        self._analysis_budget = budget


def test_small_function_passes_the_deferred_proof_preflight():
    function = ast.parse('def decorate(cls):\n    return cls\n').body[0]

    assert _within_function_budget(Analyzer(), function) is True


def test_function_over_the_local_node_limit_is_rejected():
    statements = '\n'.join('    value_%d = %d' % (index, index) for index in range(1000))
    function = ast.parse('def decorate(cls):\n' + statements + '\n').body[0]

    assert _within_function_budget(Analyzer(), function) is False


def test_external_work_budget_exhaustion_propagates_without_partial_acceptance():
    function = ast.parse('def decorate(cls):\n    return cls\n').body[0]
    budget = AnalysisBudget(AnalysisLimits(max_work=1))

    with pytest.raises(AnalysisLimitExceeded, match='work limit exceeded'):
        _within_function_budget(Analyzer(budget), function)
