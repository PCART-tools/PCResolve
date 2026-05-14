## @package tests.test_single_file
#  Unit tests for the SingleFileAnalyzer (ported from test_ast.py).

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import ast
from pcresolve.single_file import analyze_source, SingleFileAnalyzer


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


def test_binop_receiver_and_broken_chain():
    """Methods called on BinOp results and across Call-broken attribute
    chains should be detected as API calls, and intermediate attribute
    accesses should be traced."""
    code = """import polars as pl
result = ((pl.col("time") - pl.col("time").first()).last().dt.days() + 1).alias("days_in_month")
"""
    result = analyze_source(code)
    expressions = [c.expression for c in result.api_calls]

    # .first() chain: pl.col('time') and pl.col('time').first()
    assert any(".first()" in e for e in expressions), \
        f"Missing .first() call in {expressions}"

    # .last() on BinOp(Sub) receiver
    assert any("last()" in e for e in expressions), \
        f"Missing .last() call on BinOp receiver in {expressions}"

    # .days() across Call-broken attribute chain (.last().dt.days)
    assert any(".dt.days()" in e for e in expressions), \
        f"Missing .days() call across broken chain in {expressions}"

    # .alias() on BinOp(Add) receiver
    assert any("alias" in e and "days_in_month" in e for e in expressions), \
        f"Missing .alias() call on BinOp receiver in {expressions}"

    # .dt attribute access on a Call result should be tracked
    tree = ast.parse(code)
    tracer = SingleFileAnalyzer()
    tracer.visit(tree)
    attr_strings = [a['attr'] for a in tracer.attr_accesses]
    assert any(".dt" in a for a in attr_strings), \
        f"Missing .dt attribute access in {attr_strings}"


def test_def_symbol_stays_local_after_return():
    """visit_Return must NOT overwrite symbols.direct for a def function.

    A locally defined function's symbol source must remain "local" even
    when the function returns a third-party API result.  Return-value
    flow belongs in a separate channel (return_sources).
    """
    code = """import requests
def fetch(url):
    return requests.get(url)
"""
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    assert tracer.symbols.direct.get("fetch") == "local", (
        f"Expected 'local', got {tracer.symbols.direct.get('fetch')}"
    )


def test_return_value_flow_via_trace_source():
    """trace_source on a call to a local function should follow return flow.

    data = fetch(url) where fetch returns requests.get(url) —
    trace_source should resolve through the return flow to "requests".
    """
    code = """import requests
def fetch(url):
    return requests.get(url)

data = fetch("http://example.com")
"""
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    # Symbol chain for data should end with "requests"
    chain = tracer.symbols.trace("data")
    assert chain[-1] == "requests", f"Expected requests, got chain: {chain}"


def test_local_function_call_classified_as_local():
    """Call to locally defined function → top = 'local'."""
    code = """import requests
def fetch(url):
    return requests.get(url)

result = fetch("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    # The call fetch('http://example.com') should be local
    fetch_calls = [e for e in calls if "fetch(" in e]
    assert fetch_calls, "fetch(...) call not found in api_calls"
    assert calls[fetch_calls[0]] == "local", (
        f"Expected local, got {calls[fetch_calls[0]]}"
    )


def test_alias_to_thirdparty_is_thirdparty():
    """f = requests.get; f(url) → third-party (alias, not new def)."""
    code = """import requests
get_req = requests.get
result = get_req("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    alias_calls = [e for e in calls if "get_req(" in e]
    assert alias_calls, "get_req(...) call not found in api_calls"
    assert calls[alias_calls[0]] == "requests", (
        f"Expected requests, got {calls[alias_calls[0]]}"
    )


def test_partial_of_thirdparty_is_thirdparty():
    """functools.partial of third-party → still third-party (preserves identity)."""
    code = """from functools import partial
import requests
fetcher = partial(requests.get, timeout=10)
result = fetcher("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    partial_calls = [e for e in calls if "fetcher(" in e]
    assert partial_calls, "fetcher(...) call not found in api_calls"
    assert calls[partial_calls[0]] == "requests", (
        f"Expected requests, got {calls[partial_calls[0]]}"
    )


def test_locally_defined_class_method_is_local():
    """client.method() where method is defined in local class body → local."""
    code = """import requests
class Client:
    def get(self, url):
        return requests.get(url)

c = Client()
c.get("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    method_calls = [e for e in calls if "c.get(" in e]
    assert method_calls, "c.get(...) call not found in api_calls"
    # c.get resolves through _resolve_methods → returns "get" (string)
    # "get" is in defined_functions → should be local
    assert calls[method_calls[0]] == "local", (
        f"Expected local, got {calls[method_calls[0]]}"
    )


def test_inherited_method_from_thirdparty_base():
    """Method inherited from third-party base class → third-party."""
    code = """from requests import Session
class MySession(Session):
    pass

s = MySession()
s.get("http://example.com")
"""
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    # The call s.get(...) has a tuple base ("instance_method", "s", "get").
    # It must NOT be dropped — it should be recorded so cross_file can resolve.
    get_calls = [c for c in tracer.api_calls if "s.get(" in c["api"]]
    assert get_calls, (
        "s.get(...) call was dropped — tuple base not handled"
    )


def test_multi_level_attribute_chain_on_imported_class():
    """obj.attr.method() where obj comes from an imported class → third-party."""
    code = """from flask import Flask
app = Flask(__name__)
app.logger.info("hello")
"""
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    info_calls = [c for c in tracer.api_calls if "info(" in c["api"]]
    assert info_calls, "info(...) call not found in api_calls"
    # app.logger.info should have base = ("instance_method", "Flask", "info")
    # since the root "app" traces to Flask, an imported class
    base = info_calls[0]["base"]
    assert isinstance(base, tuple), f"Expected tuple base, got {base!r}"
    assert base[0] == "instance_method", f"Expected instance_method, got {base[0]!r}"
    assert base[1] == "Flask", f"Expected Flask as class, got {base[1]!r}"


def test_multi_level_attribute_chain_on_imported_name():
    """imported_name.attr.method() where root is directly imported → third-party."""
    code = """from flask import request
request.headers.get("Authorization")
"""
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    get_calls = [c for c in tracer.api_calls if ".get(" in c["api"]]
    assert get_calls, ".get(...) call not found in api_calls"
    # request.headers.get should have base = ("instance_method", "request", "get")
    # since the root "request" is directly imported from flask
    base = get_calls[0]["base"]
    assert isinstance(base, tuple), f"Expected tuple base, got {base!r}"
    assert base[0] == "instance_method", f"Expected instance_method, got {base[0]!r}"
    assert base[1] == "request", f"Expected request as class, got {base[1]!r}"


if __name__ == "__main__":
    test_basic_imports()
    test_alias_imports()
    test_from_import()
    test_local_function()
    test_local_class()
    test_decorator_binding()
    test_api_calls_collected()
    test_binop_receiver_and_broken_chain()
    test_def_symbol_stays_local_after_return()
    test_return_value_flow_via_trace_source()
    test_local_function_call_classified_as_local()
    test_alias_to_thirdparty_is_thirdparty()
    test_partial_of_thirdparty_is_thirdparty()
    test_locally_defined_class_method_is_local()
    test_inherited_method_from_thirdparty_base()
    test_multi_level_attribute_chain_on_imported_class()
    test_multi_level_attribute_chain_on_imported_name()
    print("All SingleFileAnalyzer tests passed.")
