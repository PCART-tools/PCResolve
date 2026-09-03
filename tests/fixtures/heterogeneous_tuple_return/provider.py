import json
import numpy as np


def make_mixed():
    return np.array([1, 2]), json.loads('"text"')
