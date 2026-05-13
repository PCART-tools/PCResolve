import requests
import numpy as np

def abc():
    arr=np.array([1,2,3])
    return arr.argmax()

class UserClient:
    def __init__(self,base_url):
        self.base_url=base_url
        self.session=requests.Session()

    def get_user(self,uid):
        url=f"{self.base_url}/users/{uid}"
        resp=self.session.get(url)
        return resp.json()

def _returns_requests_get():
    return requests.get
a=_returns_requests_get()("https://api.example.com/status")