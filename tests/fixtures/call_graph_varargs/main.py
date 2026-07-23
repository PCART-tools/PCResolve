import numpy as np
import pandas as pd

from helper import forward_kwargs, forward_varargs


array_value = np.array([1, 2])
frame_value = pd.read_csv("data.csv")
forward_varargs(array_value)
forward_varargs(array_value, frame_value)
forward_kwargs(value=array_value)
