import numpy as np

from helper import stream


array_value = np.array([1, 2])
for item in stream(array_value):
    item.reshape(1, -1)
