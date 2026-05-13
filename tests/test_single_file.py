## @package tests.test_single_file
#  Unit tests for the SingleFileAnalyzer (ported from test_ast.py).

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve.single_file import analyze_source


def test_basic_imports():
    code = """import requests
from flask import Flask
import numpy as np

resp = requests.get("https://example.com")
app = Flask(__name__)
data = np.array([1, 2, 3])"""
    result = analyze_source(code)
    tops = {s: result.symbols.get(s) for s in result.symbols}
    chains = result.chains
    assert chains.get("app")[-1] == "flask", f"Expected flask, got {chains.get('app')}"
    assert chains.get("resp")[-1] == "requests", f"Expected requests, got {chains.get('resp')}"
    assert chains.get("data")[-1] == "numpy", f"Expected numpy, got {chains.get('data')}"


def test_alias_imports():
    code = """import requests as req
from flask import Flask as F
import numpy as np

r = req.get("https://example.com")
app = F(__name__)
arr = np.array([1, 2, 3])"""
    result = analyze_source(code)
    chains = result.chains
    assert chains.get("r")[-1] == "requests"
    assert chains.get("app")[-1] == "flask"
    assert chains.get("arr")[-1] == "numpy"


def test_from_import():
    code = """from os.path import join
p = join("a", "b")"""
    result = analyze_source(code)
    chains = result.chains
    assert chains.get("p")[-1] == "os.path"


def test_local_function():
    code = """import requests
def my_wrapper():
    pass
result = my_wrapper()"""
    result = analyze_source(code)
    chains = result.chains
    assert chains.get("my_wrapper")[-1] == "local"


def test_local_class():
    code = """import requests
class MyClass:
    def method(self):
        return requests.post("url")
obj = MyClass()"""
    result = analyze_source(code)
    chains = result.chains
    assert chains.get("MyClass")[-1] == "local"


def test_decorator_binding():
    code = """from flask import Flask
app = Flask(__name__)
@app.route('/')
def index():
    return 'hello'"""
    result = analyze_source(code)
    chains = result.chains
    assert chains.get("app")[-1] == "flask"


def test_api_calls_collected():
    code = """import requests
requests.get('http://example.com')
requests.post('http://example.com', data={'k': 'v'})"""
    result = analyze_source(code)
    api_calls = [c.expression for c in result.api_calls]
    assert any("get" in c for c in api_calls)
    assert any("post" in c for c in api_calls)


if __name__ == "__main__":
    test_basic_imports()
    test_alias_imports()
    test_from_import()
    test_local_function()
    test_local_class()
    test_decorator_binding()
    test_api_calls_collected()
    print("All SingleFileAnalyzer tests passed.")
