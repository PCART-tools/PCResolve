import numpy as np


def stream(value):
    yield value


array_value = np.array([1, 2])
for item in stream(array_value):
    item.reshape(1, -1)


def list_stream(value):
    yield value


items = []
for item in list_stream(items):
    item.append(1)
