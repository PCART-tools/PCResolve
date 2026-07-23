import numpy as np


def api_2(value):
    return value.reshape((1, -1))


def api_3(value):
    return api_2(value)


def api_4(x, y):
    b = x + y
    return api_3(b)


api_4(np.array([1, 2]), np.array([3, 4]))
