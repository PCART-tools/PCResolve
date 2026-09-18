from pandas.core.series import Series, Series as SeriesAlias
from pandas.core.generic import ABCSeries
import pandas as pd
import numpy as np


def cases(arg, values):
    TypeError('arg must be a string, datetime, list, tuple, 1-d array, or Series')
    isinstance(arg, ABCSeries)
    isinstance(arg, Series)
    Series(values)
    pd.Series(values)
    SeriesAlias(values)
    ABCSeries(values)
    SeriesExtra(values)
    Series.to_numpy(arg)
    TypeError('np.array is expected')
    np.array(values)
    np.array_equal(values, values)
