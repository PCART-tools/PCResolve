import multiprocessing as mp
import numpy as np


class Holder:
    def __init__(self, job):
        self.values = np.zeros(2)
        self.results = job.map(str, [1])
        self.pool = mp.Pool()

    def run(self):
        self.values.reshape(1)
        self.values[0].reshape(1)
        self.values[0].reshape(1).dot(self.values[0])
        self.values[0].reshape(1).dot(self.values[0]).dot(self.values[0])
        self.results.append(2)
        self.pool.close()
