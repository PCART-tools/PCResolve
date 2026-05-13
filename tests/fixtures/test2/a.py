# a.py
from b import fetch
result=fetch(1)
# b.py
import requests
def fetch(id):
    return requests.get(f"https://api.com/users/{id}")


