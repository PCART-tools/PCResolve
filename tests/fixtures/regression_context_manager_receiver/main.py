# 1.0.5 Task C: context manager receiver ownership.
# Uses real third-party names so PCResolve treats them as external.

import requests
from requests import Session
import requests as rq


# === Scenario 1: Direct constructor ===
with Session() as s1:
    s1.get("/")


# === Scenario 2: Alias constructor ===
with rq.Session() as s2:
    s2.post("/")


# === Scenario 3: Module import constructor ===
with requests.Session() as s3:
    s3.get("/")


# === Scenario 4: Local factory return ===
def make_session():
    return Session()


with make_session() as s4:
    s4.get("/")


# === Negative: open() must stay python ===
with open("/tmp/x") as f:
    f.read()


# === Negative: local unknown CM ===
class LocalCM:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


with LocalCM() as obj:
    obj.run()


# === Cross-file factory chain ===
from factory import create_app

with create_app().test_client() as client:
    client.get("/")
