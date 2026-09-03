import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "local_expression_return_flow"
)


def _calls():
    result = analyze_project(FIXTURE)
    return {
        (call.lineno, call.expression): call
        for call in result.all_api_calls
    }


def test_expression_return_uses_exact_numpy_call_context():
    assert _calls()[(15, "numpy_result.sum()")].top_library == "numpy"


def test_expression_return_uses_exact_pandas_call_context():
    assert _calls()[(18, "series_result.mean()")].top_library == "pandas"


def test_uncalled_expression_return_stays_unknown():
    assert _calls()[(11, "result.sum()")].top_library == "unknown"
