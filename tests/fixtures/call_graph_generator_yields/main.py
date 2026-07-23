import numpy as np


def array_stream():
    yield np.array([1, 2])


def list_stream():
    yield []


for array_value in array_stream():
    array_value.reshape(1, -1)

for list_value in list_stream():
    list_value.append(1)

for rebound_value in array_stream():
    rebound_value.reshape(1, -1)

rebound_value = []
rebound_value.append(1)
