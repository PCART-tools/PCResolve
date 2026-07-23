import json
import numpy as np


def first_array(value):
    return np.array(value)


def second_array(value):
    return np.asarray(value)


def python_value(value):
    return json.loads(value)


def no_value(value):
    value
