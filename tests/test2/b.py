import requests

def fetch(id):
    return requests.get(f"https://api.com/users/{id}")