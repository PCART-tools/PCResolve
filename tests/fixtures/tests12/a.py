from flask import Flask
import requests

app=Flask(__name__)


def fetch_and_print(func): #TODO:保存函数参数列表
    def wrapper(url):
        resp=requests.get(url)
        return func(resp)
    return wrapper

@app.route("/hello")
def hello():
    return "hello"

@fetch_and_print
def handle_response(a):
    return a.text

result=handle_response("https://example.com")

def class_ping_decorator(cls):
    def wrapped(*args,**kwargs):
        requests.get("https://example.com/ping")
        return cls(*args,**kwargs)
    return wrapped

@class_ping_decorator
class DecoratedClient:
    def __init__(self):
        self.ok=True

dc=DecoratedClient()
