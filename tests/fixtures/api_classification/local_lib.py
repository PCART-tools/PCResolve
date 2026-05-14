import requests
from functools import partial


def fetch_data(url):
    """Local function wrapping third-party API."""
    return requests.get(url)


class LocalClient:
    """Class whose get method is locally defined."""
    def get(self, url):
        return requests.get(url)


class MixedClient(LocalClient):
    """Inherits get from local base — should still be local."""
    pass


from requests import Session


class ThirdPartyClient(Session):
    """Class whose get method is inherited from a third-party base."""
    pass


def wrapper(url):
    """Local function calling another local function."""
    return fetch_data(url)


get_alias = requests.get

fetcher = partial(requests.get, timeout=10)
