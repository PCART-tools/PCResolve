from pcresolve.cross_file import analyze_project


FIXTURE = "tests/fixtures/call_graph_rebinding"


def _calls():
    return analyze_project(FIXTURE).all_api_calls


def test_rebinding_invalidates_previous_receiver_flow():
    calls = [call for call in _calls() if call.expression == "view.reshape(1, -1)"]

    assert len(calls) == 2
    assert calls[0].top_library == "numpy"
    # The rebinding is known to produce a Python value.  The important
    # contract is that the stale NumPy flow is not reused.
    assert calls[1].top_library == "python"


def test_rebinding_fixture_keeps_call_site_coverage():
    expressions = [call.expression for call in _calls()]

    assert expressions.count("view.reshape(1, -1)") == 2
