import numpy as np
import pandas as pd


def combine(left, right):
    return left + right


def unresolved(left, right):
    result = combine(left, right)
    return result.sum()


numpy_result = combine(np.array([1]), np.array([2]))
numpy_result.sum()

series_result = combine(pd.Series([1]), pd.Series([2]))
series_result.mean()
