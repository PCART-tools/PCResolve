"""Probe the receiver type of a NumPy comparison expression."""

import numpy as np


def main():
    W = np.eye(3)
    comparison = np.diag(W) == np.zeros(W.shape[0])
    method = comparison.any

    print("comparison type:", type(comparison))
    print("method owner module:", type(method).__module__)
    print("bound self:", method.__self__ is comparison)
    print("result type:", type(method()))

    assert type(comparison).__module__ == "numpy"
    assert type(comparison).__name__ == "ndarray"
    assert method.__self__ is comparison
    assert type(method()).__module__ == "numpy"


if __name__ == "__main__":
    main()
