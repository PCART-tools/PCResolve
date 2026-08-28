"""Targeted regression tests: pandas/numpy/scipy receiver ownership."""

import pytest
from pcresolve.cross_file import analyze_project
import os

FIXTURE = os.path.join(os.path.dirname(__file__),
                       "fixtures", "receiver_ownership")


def _find(calls, prefix):
    for c in calls:
        if c.expression.startswith(prefix):
            return c
    return None


def _top(calls, prefix):
    c = _find(calls, prefix)
    assert c is not None, f"call starting with '{prefix}' not found"
    return c.top_library


@pytest.fixture(scope="module")
def result():
    return analyze_project(FIXTURE)


# ======================================================================
# Group A: Direct construction — must pass (regression safety)
# ======================================================================

def test_direct_pandas_dropna(result):
    assert _top(result.all_api_calls, "df.dropna(") == "pandas"

def test_direct_pandas_cumsum(result):
    assert _top(result.all_api_calls, "s.cumsum(") == "pandas"

def test_direct_pandas_between_time(result):
    assert _top(result.all_api_calls, "s.between_time(") == "pandas"

def test_direct_numpy_reshape(result):
    assert _top(result.all_api_calls, "arr.reshape(") == "numpy"

def test_direct_numpy_flatten(result):
    assert _top(result.all_api_calls, "arr.flatten(") == "numpy"

def test_direct_numpy_mean(result):
    assert _top(result.all_api_calls, "arr.mean(") == "numpy"

def test_direct_scipy_todense(result):
    assert _top(result.all_api_calls, "m.todense(") == "scipy"


# ======================================================================
# Group B: Conversion boundary — must pass
# ======================================================================

def test_to_numpy_call_owner_is_pandas(result):
    """data.to_numpy() call itself is a pandas API call."""
    assert _top(result.all_api_calls, "data.to_numpy(") == "pandas"

def test_after_to_numpy_reshape_is_numpy(result):
    """data = data.to_numpy(); data.reshape(...) receiver is ndarray."""
    assert _top(result.all_api_calls, "x.reshape(") == "numpy"

def test_values_flatten_is_numpy(result):
    """data.values → ndarray, .flatten() is numpy."""
    assert _top(result.all_api_calls, "vals.flatten(") == "numpy"


# ======================================================================
# Group C: Receiver-preserving chain (KNOWN FAILURE)
#   np.log(pd.Series) preserves pandas receiver
# ======================================================================

def test_np_log_pandas_diff_is_pandas(result):
    """Probe-confirmed: np.log(pd.Series).diff() receiver is pandas."""
    assert _top(result.all_api_calls, "log_price.diff(") == "pandas"


def test_np_log_dropna_diff_is_pandas(result):
    """np.log(price.dropna()).diff() — nested arg, preserves pandas."""
    assert _top(result.all_api_calls, "np.log(price.dropna()).diff(") == "pandas"


def test_np_array_dropna_reshape_is_numpy(result):
    """np.array(price.dropna()).reshape() — NOT receiver-preserving."""
    assert _top(result.all_api_calls, "np.array(price.dropna()).reshape(") == "numpy"


def test_np_log_to_numpy_reshape_is_numpy(result):
    """np.log(data.to_numpy()).reshape() — conversion boundary respected."""
    assert _top(result.all_api_calls, "np.log(data.to_numpy()).reshape(") == "numpy"


def test_np_log_values_reshape_is_numpy(result):
    """np.log(data.values).reshape() — attribute conversion respected."""
    assert _top(result.all_api_calls, "np.log(data.values).reshape(") == "numpy"


# ======================================================================
# Group D: SciPy-to-NumPy return boundary (KNOWN FAILURE)
#   cdist(...) returns numpy.ndarray
# ======================================================================

def test_cdist_argmin_is_numpy(result):
    """Probe-confirmed: cdist() returns ndarray, .argmin() is numpy."""
    assert _top(result.all_api_calls, "D.argmin(") == "numpy"

def test_cdist_mean_is_numpy(result):
    """Probe-confirmed: cdist() returns ndarray, .mean() is numpy."""
    assert _top(result.all_api_calls, "D.mean(") == "numpy"


# ======================================================================
# Group E: Parameter receiver (KNOWN FAILURE)
#   These need parameter provenance propagation but are low-impact
#   for the current round.
# ======================================================================

@pytest.mark.xfail(reason="parameter receiver provenance needs call-graph propagation")
def test_param_pandas_dropna(result):
    assert _top(result.all_api_calls, "df_param.dropna(") == "pandas"

@pytest.mark.xfail(reason="parameter receiver provenance needs call-graph propagation")
def test_param_numpy_reshape(result):
    assert _top(result.all_api_calls, "arr_param.reshape(") == "numpy"


# ======================================================================
# Group F: Factory return — verify current behavior
# ======================================================================

def test_factory_make_dataframe_is_local(result):
    """Local function call itself is local."""
    assert _top(result.all_api_calls, "make_dataframe(") == "local"

def test_factory_dropna_is_pandas(result):
    """d.dropna() where d = make_dataframe() -> pd.DataFrame: receiver
    is tracked through return source."""
    assert _top(result.all_api_calls, "d.dropna(") == "pandas"


# ======================================================================
# Group G: NumPy constructor — must pass (NOT receiver-preserving)
# ======================================================================

def test_numpy_constructor_reshape_is_numpy(result):
    """np.array(pd.Index) returns ndarray, not pandas."""
    assert _top(result.all_api_calls, "a.reshape(") == "numpy"
