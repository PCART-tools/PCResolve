import numpy as np
import pandas as pd


def transform(value):
    return np.exp(value)


def unresolved(value):
    transformed = transform(value)
    return transformed.sum()


array_value = transform(np.array([1, 2]))
array_value.sum()

series_value = transform(pd.Series([1, 2]))
series_value.diff()

