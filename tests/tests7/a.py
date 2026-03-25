import requests
import pandas

HTTP_METHODS={
    "GET": requests.get,
    "POST": requests.post,
    "POOL": pandas.get,
}

func_get=HTTP_METHODS["GET"]
func_post=HTTP_METHODS["POST"]
func_pool=HTTP_METHODS["POOL"]

resp1=func_get("https://example.com")
resp2=func_post("https://example.com")
pool=func_pool()
