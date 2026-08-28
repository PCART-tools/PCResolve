import os

from pcresolve import analyze_project


FIXTURE = os.path.join(
    os.path.dirname(__file__), "fixtures", "local_ufunc_return_flow"
)


def _calls():
    result = analyze_project(FIXTURE)
    return {
        (call.lineno, call.expression): call
        for call in result.all_api_calls
    }


def test_local_ufunc_return_uses_exact_numpy_call_argument():
    call = _calls()[(15, "array_value.sum()")]
    assert call.top_library == "numpy"


def test_local_ufunc_return_uses_exact_pandas_call_argument():
    call = _calls()[(18, "series_value.diff()")]
    assert call.top_library == "pandas"


def test_uncalled_forwarded_ufunc_parameter_stays_unknown():
    call = _calls()[(11, "transformed.sum()")]
    assert call.top_library == "unknown"

