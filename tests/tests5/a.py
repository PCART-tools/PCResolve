import requests

http_get=requests.get
resp1=http_get("https://api.example.com/users/1")

HTTP_METHODS={
    "GET":requests.get,
    "POST":requests.post,
}

def call_api(method,url):
    func=HTTP_METHODS[method]
    resp=func(url)
    return resp

def make_client(base_url):
    session=requests.Session()
    def get(path):
        return session.get(base_url+path)
    return get

get_user=make_client("https://api.example.com")
resp2=get_user("/users/1")
print(resp2)
abc=call_api("GET","https://api.example.com/users/1")