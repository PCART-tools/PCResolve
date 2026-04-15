import requests
import numpy as np
import aiohttp

with requests.Session() as session:
    r1=session.get("https://example.com")

async def run():
    async with aiohttp.ClientSession() as client:
        data=client.get("https://example.com")
    return data

FUNCS=[requests.get,np.sum]
for f in FUNCS:
    out=f("https://example.com")

async def iterate(it):
    async for item in it:
        val=item
    return val
