import numpy as np


def use_default_array(value=np.array([1, 2])):
    return value.reshape(1, -1)


def use_default_list(value=[]):
    return value.append(1)


def use_default_keyword(*, value=np.array([3, 4])):
    return value.reshape(1, -1)
