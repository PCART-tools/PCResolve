# 1.0.5 P1: Receiver Object Ownership — comprehensive fixture.
# Uses real third-party module names so PCResolve treats them as external.

from requests import Session
import requests as rq
from flask import Flask


# === Scenario 1: Direct constructor binding ===
s1 = Session()
s1.get("/")


# === Scenario 2: Alias constructor binding ===
s2 = rq.Session()
s2.get("/")


# === Scenario 3: From-import constructor/factory ===
app = Flask(__name__)
app.test_client()
app.route("/")


# === Scenario 4: Local factory return ===
def make_session():
    return Session()


s4 = make_session()
s4.get("/")


# === Scenario 5: Local factory -> class attribute -> method ===
class Wrapper:
    def __init__(self):
        self.backend = make_session()

    def fetch(self):
        return self.backend.get("/")


w = Wrapper()
w.fetch()


# === Scenario 6: Cross-file factory (alias import) ===
from factory import make_session as cross_make

s6 = cross_make()
s6.get("/")


# === Scenario 6b: Cross-file factory (direct import) ===
from factory import make_session

s6b = make_session()
s6b.get("/")


# === Negative guards ===
# 6a: local string methods stay local
text = "  hello  "
text = text.strip()
text = text.replace("h", "H")

# 6b: reassigned constructor variable must not carry old provenance
s_guard = Session()
s_guard = "reassigned"
s_guard.strip()
