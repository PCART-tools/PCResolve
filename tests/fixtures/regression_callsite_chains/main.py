import requests
import numpy as np


def first():
    x = requests.Session()
    x.get("https://example.com")


def second():
    x = np.array([1])
    x.reshape((1, 1))
