import numpy as np


class Objective:
    def __call__(self, x):
        return x.reshape(1, -1)
