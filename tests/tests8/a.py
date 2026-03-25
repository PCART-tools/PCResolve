import requests
from functools import partial
import numpy as np
a=partial
get_json = a(requests.get, headers={"Accept": "application/json"})
post_data = partial(requests.post, timeout=30)
sqrt_arr = partial(np.sqrt)

resp1 = get_json("https://api.example.com/users/1")
resp2 = post_data("https://api.example.com/data", json={"key": "value"})
result = sqrt_arr([1, 4, 9])


http_get = lambda url: requests.get(url, timeout=10)
array_sum = lambda arr: np.sum(arr)
make_request = lambda url: requests.Session().get(url)

resp3 = http_get("https://example.com")
total = array_sum([1, 2, 3, 4, 5])
resp4 = make_request("https://example.com/api")

get_with_auth = lambda token: partial(requests.get, headers={"Authorization": token})