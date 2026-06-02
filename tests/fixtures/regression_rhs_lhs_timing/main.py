# Regression fixture: RHS/LHS assignment timing (1.0.5 P0).
#
# In `data_pa = pd.Series(data_pa.flatten(), ...)`, the RHS sub-call
# `data_pa.flatten()` must use the pre-assignment symbol state.
# data_pa.flatten() should resolve to numpy (the old value from
# _preaverage), NOT pandas (the new value from this assignment).

import numpy as np
import pandas as pd


def _preaverage(data, weight):
    return np.array(data) * weight


index = [0, 1, 2]
data = [1.0, 2.0, 3.0]
weight = 0.5

# data_pa starts as numpy ndarray from _preaverage
data_pa = _preaverage(data, weight)

# RHS sub-call data_pa.flatten() references data_pa BEFORE this
# assignment completes.  It must resolve to numpy (the old value),
# not pandas.
data_pa = pd.Series(data_pa.flatten(), index=index)
