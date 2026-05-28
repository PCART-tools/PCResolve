import requests
import numpy as np


def make(flag):
    if flag:
        return requests.Session()
    return np.array([1])


value = make(True)
value.get("https://example.com")
