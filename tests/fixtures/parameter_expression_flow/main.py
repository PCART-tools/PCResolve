from package_a import combine
import numpy as np
import json


def api_2(value):
    return value


def api_1(x, y):
    b = x + y
    return api_2(b)


def api_3(x, y):
    return (x + y).any()


def api_4(unresolved_x, unresolved_y):
    return (unresolved_x + unresolved_y).any()


def api_5(y):
    result = np.array([1, 2]) - y
    return result.dot(result)


def api_6(y):
    result = np.array([1, 2]) - y
    return result.dot(result)


def local_same_owner_expression():
    left = np.array([1, 2])
    result = left + np.array([3, 4])
    return result.reshape((2, 1))


def local_owner_and_python_scalar():
    result = np.array([1, 2]) + 1
    return result.reshape((2, 1))


def local_conflicting_owner_expression():
    result = np.array([1, 2]) + json.loads("[3, 4]")
    return result.reshape((2, 1))


api_1(combine(), combine())
api_3(np.array([1]), np.array([2]))
api_5(np.array([3, 4]))
api_6(json.loads("[3, 4]"))
local_same_owner_expression()
local_owner_and_python_scalar()
local_conflicting_owner_expression()
