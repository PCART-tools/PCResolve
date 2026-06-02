## @package tests.test_regression_rhs_lhs_timing
#  1.0.5 P0: RHS sub-calls must use pre-assignment symbol state.

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project


_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "regression_rhs_lhs_timing")


def test_rhs_subcall_not_contaminated_by_target():
    """data_pa.flatten() in data_pa = pd.Series(data_pa.flatten(), ...)
    must not resolve to pandas."""
    r = analyze_project(_FIXTURE)
    flatten_calls = [c for c in r.all_api_calls
                     if "flatten" in c.func_name]
    assert flatten_calls, "data_pa.flatten() not collected"
    for c in flatten_calls:
        assert c.top_library != "pandas", \
            f"RHS data_pa.flatten() must not be pandas, got {c.top_library}"


def test_rhs_subcall_uses_pre_assignment_state():
    """data_pa.flatten() should resolve based on _preaverage's return,
    not the pd.Series target."""
    r = analyze_project(_FIXTURE)
    flatten_calls = [c for c in r.all_api_calls
                     if "flatten" in c.func_name]
    assert flatten_calls
    for c in flatten_calls:
        assert c.top_library in ("local", "numpy", "python"), \
            f"data_pa.flatten() should be local/numpy/python, got {c.top_library}"


def test_pd_series_still_pandas():
    """pd.Series(...) must still resolve to pandas (not affected by timing fix)."""
    r = analyze_project(_FIXTURE)
    series_calls = [c for c in r.all_api_calls
                    if "Series" in c.func_name]
    assert series_calls, "pd.Series() not collected"
    for c in series_calls:
        assert c.top_library == "pandas", \
            f"pd.Series() must be pandas, got {c.top_library}"
