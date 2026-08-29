"""Targeted regression fixture: pandas/numpy/scipy receiver ownership.

PCResolve must classify the CALLABLE OWNER of each call expression.
Return-type inference affects SUBSEQUENT receiver calls, not the
current call expression.

pandas → library/pandas.  numpy → library/numpy.  scipy → library/scipy.
local → project-local function.
"""

import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
from scipy.sparse import csr_matrix

# ======================================================================
# Group A: Direct construction (should already pass — regression safety)
# ======================================================================

df = pd.DataFrame({"a": [1, 2, 3]})
df.dropna()                         # pandas
s = pd.Series([1.0, 2.0, 3.0])
s.cumsum()                          # pandas
s.between_time("10:00", "14:00")    # pandas
arr = np.array([1.0, 2.0, 3.0])
arr.reshape(1, -1)                  # numpy
arr.flatten()                       # numpy
arr.mean()                          # numpy
m = csr_matrix([[1.0, 0.0], [0.0, 2.0]])
m.todense()                         # scipy


# ======================================================================
# Group B: Conversion boundary — call owner vs return owner
# ======================================================================

def use_conversion():
    data = pd.DataFrame({"x": [1, 2]})
    # to_numpy() call is pandas; return is ndarray
    data.to_numpy()                  # pandas

    # after to_numpy, receiver is ndarray
    x = data.to_numpy()
    x.reshape(1, -1)                 # numpy

    # .values attribute conversion
    data2 = pd.Series([1.0, 2.0])
    vals = data2.values
    vals.flatten()                   # numpy


# ======================================================================
# Group C: Receiver-preserving chain (np.log + pandas)
#   Probe: type(np.log(pd.Series(...))) is pd.Series
# ======================================================================

def use_receiver_preserving():
    price = pd.Series([10.0, 12.0, 15.0])
    log_price = np.log(price)        # numpy call
    log_price.diff()                 # pandas — np.log preserves receiver

    # Nested argument: np.log(price.dropna()).diff()
    # price.dropna() receiver is pandas → np.log preserves → .diff() is pandas
    np.log(price.dropna()).diff()    # pandas

    # Negative: np.array(price.dropna()).reshape() — NOT receiver-preserving
    # np.array returns ndarray, not pandas
    np.array(price.dropna()).reshape(1, -1)  # numpy

    # Conversion boundary inside ufunc arg:
    # data.to_numpy() call owner=pandas, return=ndarray
    # np.log(ndarray) → ndarray → .reshape() is numpy
    data = pd.Series([10.0, 20.0])
    np.log(data.to_numpy()).reshape(1, -1)  # numpy

    # Attribute conversion inside ufunc arg:
    # data.values returns ndarray → np.log(ndarray) → .reshape() is numpy
    np.log(data.values).reshape(1, -1)      # numpy


# ======================================================================
# Group D: SciPy-to-NumPy return boundary
#   Probe: cdist(...) returns numpy.ndarray
# ======================================================================

def use_scipy_to_numpy():
    X = np.array([[1.0, 2.0], [3.0, 4.0]])
    centres = np.array([[1.0, 2.0]])
    D = cdist(X, centres)            # scipy (call owner)
    D.argmin(axis=1)                 # numpy (receiver is ndarray)
    D.mean()                         # numpy


# ======================================================================
# Group E: Uncalled parameters have no concrete receiver evidence.
# ======================================================================

def process_frame(df_param):
    df_param.dropna()                # unknown: no project call supplies a value

def process_array(arr_param):
    arr_param.reshape(-1, 1)         # unknown: no project call supplies a value


# ======================================================================
# Group F: Receiver via local function return (future: call graph)
# ======================================================================

def make_dataframe():
    return pd.DataFrame({"x": [1, 2]})

def use_factory():
    d = make_dataframe()             # local
    d.dropna()                       # local (receiver from local factory)


# ======================================================================
# Group G: NumPy constructor (NOT receiver-preserving)
# ======================================================================

def use_numpy_constructor():
    idx = pd.Index([1, 2, 3])
    a = np.array(idx)                # numpy constructor
    a.reshape(1, -1)                 # numpy (NOT pandas)
