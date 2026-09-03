import numpy as np


def reshape_first(values):
    return values[0].reshape(1, -1)


def uncalled(values):
    return values[0].reshape(2, -1)


def reshape_forwarded(values):
    return values[0].reshape(3, -1)


def forward(values):
    return reshape_forwarded(values)


def reshape_dynamic(values, key):
    return values[key].reshape(4, -1)


def forward_dynamic(values, key):
    return reshape_dynamic(values, key)


def summarize_nested(value):
    return value.mean()


def select_nested(values, key):
    return summarize_nested(values[key])


def forward_nested(values, key):
    return select_nested(values, key)


matrix = np.zeros((2, 2))
reshape_first(matrix)
forward(matrix)
forward_dynamic(matrix, 0)
forward_nested(matrix, 0)
