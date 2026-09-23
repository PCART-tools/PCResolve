# Reduced from Tornado 6.0 and Tornado 3.0 tornado/httpclient.py.
class Configurable:
    def __new__(cls, io_loop=None, **kwargs):
        return object.__new__(cls)


class HTTPRequest:
    def __init__(self, url, method="GET", headers=None):
        self.url = url


class AsyncHTTPClient(Configurable):
    def __new__(cls, io_loop=None, **kwargs):
        return super(AsyncHTTPClient, cls).__new__(cls, io_loop, **kwargs)

    def fetch(self, request, **kwargs):
        return HTTPRequest(url=request, **kwargs)
