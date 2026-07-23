import os


from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "callable_object_forwarding")


def test_local_callable_object_forwards_call_argument_owner():
    """A uniquely resolved local __call__ receives the argument owner."""
    analysis = analyze_project(FIXTURE, scope_model="v2")
    matches = [
        call for call in analysis.all_api_calls
        if call.func_name == "x.reshape"
    ]
    assert len(matches) == 1
    assert matches[0].top_library == "numpy"
