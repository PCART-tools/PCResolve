import numpy as np


class Holder:
    def __init__(self, values):
        self.left = np.zeros(2)
        self.right = np.ones(2)
        self.combined = self.left + self.right
        self.combined.reshape(1)

        self.values = values
        self.mixed = self.values + self.right
        self.mixed.reshape(1)
