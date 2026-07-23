import numpy as np


def array_stream():
    yield np.array([1, 2])


def list_stream():
    yield []
