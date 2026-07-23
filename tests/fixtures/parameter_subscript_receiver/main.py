import numpy as np


def reshape_first(values):
    return values[0].reshape(1, -1)


def uncalled(values):
    return values[0].reshape(2, -1)


matrix = np.zeros((2, 2))
reshape_first(matrix)
