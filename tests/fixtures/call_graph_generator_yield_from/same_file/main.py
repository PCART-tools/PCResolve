import numpy as np


def inner(value):
    yield value


def outer(value):
    yield from inner(value)


array_value = np.array([1, 2])
for item in outer(array_value):
    item.reshape(1, -1)
