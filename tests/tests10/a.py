import requests

class UserClient:
    def __init__(self,base_url):
        self.base_url=base_url
        self.session=requests.Session()

    def get_user(self,uid):
        url=f"{self.base_url}/users/{uid}"
        resp=self.session.get(url)
        return resp.json()

client=UserClient("https://api.example.com")
user=client.get_user(1)
