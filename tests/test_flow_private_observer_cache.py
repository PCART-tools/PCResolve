## @package tests.test_flow_private_observer_cache
#  Private observer projections are reused per owner and replay their allowance.

from types import SimpleNamespace

from pcresolve.flow.model.results import FunctionRef
from pcresolve.flow.proofs.namespaces.metadata import _metadata_calls


## Build one analyzer stand-in with the fields the memo consults.
def _analyzer(budget=None):
    return SimpleNamespace(_private_observer_cache={}, _analysis_budget=budget,
                           _class_effect_fact_steps=100)


## Return the observer class and its source definition stand-in.
def _owner():
    return (FunctionRef(module='sample', qualname='Observer'), object())


def test_private_observer_results_are_reused_and_replay_the_allowance(monkeypatch):
    analyzer = _analyzer()
    invocations = []

    ## Stand-in scan that charges a fixed allowance per run.
    def uncached(active, owner):
        invocations.append(active._class_effect_fact_steps)
        active._class_effect_fact_steps -= 7
        return [{'kind': 'private_observer_data_result'}]

    monkeypatch.setattr(_metadata_calls, '_private_results_uncached', uncached)
    first = _metadata_calls._private_results(analyzer, _owner())
    second = _metadata_calls._private_results(analyzer, _owner())
    assert invocations == [100]
    assert first == second == [{'kind': 'private_observer_data_result'}]
    assert first is not second
    assert analyzer._class_effect_fact_steps == 86


def test_private_observer_results_are_not_reused_under_a_budget(monkeypatch):
    analyzer = _analyzer(budget=object())
    invocations = []

    ## Stand-in scan that charges a fixed allowance per run.
    def uncached(active, owner):
        invocations.append(active._class_effect_fact_steps)
        return []

    monkeypatch.setattr(_metadata_calls, '_private_results_uncached', uncached)
    _metadata_calls._private_results(analyzer, _owner())
    _metadata_calls._private_results(analyzer, _owner())
    assert len(invocations) == 2
    assert analyzer._private_observer_cache == {}
