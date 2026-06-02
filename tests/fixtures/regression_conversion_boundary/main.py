# Regression fixture: conversion boundary (1.0.5 P1).
#
# After data = data.to_numpy(), subsequent method calls on data
# should resolve to numpy, not pandas.

import numpy as np
import pandas as pd


def refresh_time(series_list):
    return pd.DataFrame(series_list)


# 1: Direct conversion
data = refresh_time([1, 2, 3])
data = data.to_numpy()
data = data.reshape(1, -1)        # must be numpy, not pandas

# 2: Chained conversion with attribute
data2 = refresh_time([4, 5, 6])
data2 = data2.to_numpy().T
data2 = data2.reshape(1, -1)      # must be numpy, not pandas

# 3: Values attribute
data3 = refresh_time([7, 8, 9])
data3 = data3.values
data3 = data3.reshape(1, -1)      # must be numpy, not pandas

# 4: Bare method reference — NOT a conversion
df4 = refresh_time([4, 5, 6])
converter = df4.to_numpy          # saving the method object, NOT calling it
# converter.reshape(1, -1)        # would be a follow-up call (undefined)

# 5: Assign from bare method reference — NOT a conversion
df5 = refresh_time([7, 8, 9])
df5 = df5.to_numpy                # saving method ref, NOT calling it
df5.reshape(1, -1)                # df5 is a method object; should NOT be numpy
