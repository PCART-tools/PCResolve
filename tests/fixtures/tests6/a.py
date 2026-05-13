import requests


def make_client(base_url):
    session = requests.Session()
    def get(path):
        return session.get(base_url + path)
    return get


def call_api(method, url):
    HTTP_METHODS = {
        "GET": requests.get,
        "POST": requests.post,
    }
    func = HTTP_METHODS[method]
    resp = func(url)
    return resp
