import requests
import numpy as np

session = requests.Session()


def use_param(requests):
    return requests.get("/local-like")


def use_local():
    np = requests.Session()
    return np.get("/local-session")


items = [np.array([x]) for x in range(2)]
session.get("https://example.com")
