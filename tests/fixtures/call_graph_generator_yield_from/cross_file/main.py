import numpy as np

from helper import outer


array_value = np.array([1, 2])
for item in outer(array_value):
    item.reshape(1, -1)
