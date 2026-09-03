"""Regression fixture: method calls on comparison-expression receivers.

(a == b).any() — when both sides are numpy ndarray expressions,
the comparison returns a boolean ndarray and .any() is numpy.
"""

import numpy as np


def numpy_compare_any():
    """(numpy_expr == numpy_expr).any() → numpy."""
    W = np.ones((3, 3))
    return (np.diag(W) == np.zeros(W.shape[0])).any()


def numpy_compare_all():
    """(numpy_expr == numpy_expr).all() → numpy."""
    W = np.ones((3, 3))
    return (np.diag(W) == np.zeros(W.shape[0])).all()


def local_compare():
    """(a == b).any() — local variables, not numpy."""
    a = 1
    b = 2
    return (a == b).any()
