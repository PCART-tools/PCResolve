## @package tests.test_regression_conversion_boundary
#  1.0.5 P1: after conversion calls (to_numpy, values),
#  subsequent method calls must resolve to the post-conversion library.

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project


_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "regression_conversion_boundary")


def _reshape_calls(result):
    return [c for c in result.all_api_calls
            if "reshape" in c.func_name]


def test_direct_conversion_to_numpy():
    """data.reshape after data = data.to_numpy() must be numpy."""
    r = analyze_project(_FIXTURE)
    reshapes = _reshape_calls(r)
    assert len(reshapes) >= 3
    # data.reshape (after data.to_numpy)
    assert reshapes[0].top_library == "numpy", \
        f"expected numpy, got {reshapes[0].top_library}"


def test_chained_conversion_with_dot_T():
    """data2.reshape after data2 = data2.to_numpy().T must be numpy."""
    r = analyze_project(_FIXTURE)
    reshapes = _reshape_calls(r)
    # data2.reshape (after data2.to_numpy().T)
    assert reshapes[1].top_library == "numpy", \
        f"expected numpy, got {reshapes[1].top_library}"


def test_values_attribute_conversion():
    """data3.reshape after data3 = data3.values must be numpy."""
    r = analyze_project(_FIXTURE)
    reshapes = _reshape_calls(r)
    # data3.reshape (after data3.values)
    assert reshapes[2].top_library == "numpy", \
        f"expected numpy, got {reshapes[2].top_library}"


def test_to_numpy_itself_stays_pandas():
    """data.to_numpy() itself is still a pandas API call."""
    r = analyze_project(_FIXTURE)
    to_numpy_calls = [c for c in r.all_api_calls
                      if "to_numpy" in c.func_name]
    assert len(to_numpy_calls) >= 2
    for c in to_numpy_calls:
        assert c.top_library == "pandas", \
            f"to_numpy() itself must be pandas, got {c.top_library}"


def test_bare_method_reference_not_conversion():
    """df5.reshape after df5 = df5.to_numpy (no call) must NOT be numpy."""
    r = analyze_project(_FIXTURE)
    # The reshape on df5 (line with "df5.reshape" — case 5 in fixture)
    df5_reshapes = [c for c in r.all_api_calls
                    if "df5.reshape" in c.func_name]
    assert df5_reshapes, "df5.reshape() not collected"
    for c in df5_reshapes:
        assert c.top_library != "numpy", \
            f"bare method ref must not convert to numpy, got {c.top_library}"
