## @package tests.test_classification_boundary
#  Phase 8A boundary tests: local symbols must not leak into library_usage,
#  import aliases must keep DIRECT_IMPORT classification.

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from pcresolve import analyze_project


def _run_code(code, scope_model="v2"):
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "main.py"), "w") as f:
            f.write(code)
        return analyze_project(td, scope_model=scope_model)


# ── Test 1: self.method() must not enter library_usage ──────────────────

def test_self_method_not_in_library():
    code = ("class A:\n"
            "    def helper(self):\n"
            "        pass\n"
            "    def run(self):\n"
            "        self.helper()\n"
            "A().run()\n")
    r = _run_code(code)
    for call in r.all_api_calls:
        assert "helper" not in str(call.top_library) or call.top_library == "local", \
            f"self.helper() leaked as library: {call.top_library}"
    assert "helper" not in r.library_usage


# ── Test 2: private method must not enter library_usage ────────────────

def test_private_method_not_in_library():
    code = ("class A:\n"
            "    def _add_symbol_ref(self):\n"
            "        pass\n"
            "    def run(self):\n"
            "        self._add_symbol_ref()\n"
            "A().run()\n")
    r = _run_code(code)
    assert "_add_symbol_ref" not in r.library_usage


# ── Test 3: plain local function call must be local ────────────────────

def test_local_function_is_local():
    code = ("def helper():\n"
            "    pass\n"
            "helper()\n")
    r = _run_code(code)
    helper_calls = [c for c in r.all_api_calls if "helper" in c.expression]
    assert len(helper_calls) >= 1
    for c in helper_calls:
        assert c.top_library == "local", f"helper() not local: {c.top_library}"
    assert "helper" not in r.library_usage


# ── Test 4: parameter receiver must not enter library_usage ────────────

def test_parameter_receiver_not_library():
    code = ("def f(node):\n"
            "    node.visit()\n")
    r = _run_code(code)
    for call in r.all_api_calls:
        assert call.top_library != "node", \
            f"node.visit() leaked parameter name as library"
    assert "node" not in r.library_usage


# ── Test 5: import alias must keep DIRECT_IMPORT ───────────────────────

def test_import_alias_direct_import():
    code = ("import numpy as np\n"
            "np.array([1])\n")
    r = _run_code(code)
    arr_calls = [c for c in r.all_api_calls if "array" in c.expression]
    assert len(arr_calls) >= 1
    assert arr_calls[0].top_library == "numpy"
    assert arr_calls[0].reason == "DIRECT_IMPORT", \
        f"Expected DIRECT_IMPORT, got {arr_calls[0].reason}"
    assert arr_calls[0].confidence == 1.0


# ── Test 6: from-import must keep DIRECT_IMPORT ────────────────────────

def test_from_import_direct_import():
    code = ("from numpy import array\n"
            "array([1])\n")
    r = _run_code(code)
    arr_calls = [c for c in r.all_api_calls if "array" in c.expression]
    assert len(arr_calls) >= 1
    assert arr_calls[0].top_library == "numpy"
    assert arr_calls[0].reason == "DIRECT_IMPORT", \
        f"Expected DIRECT_IMPORT, got {arr_calls[0].reason}"
    assert arr_calls[0].confidence == 1.0


# ── Test 7: self.method chain trace to external must keep provenance ───

def test_self_method_chain_to_external():
    code = ("from ext.api import Client\n"
            "class Wrapper:\n"
            "    def __init__(self, client):\n"
            "        client.open()\n"
            "        self.client = client\n"
            "    def run(self):\n"
            "        return self.client.close()\n"
            "def build():\n"
            "    c = Client()\n"
            "    w = Wrapper(c)\n"
            "    return w.run()\n")
    r = _run_code(code)
    # self.client.close() should trace to ext through constructor arg
    close_calls = [c for c in r.all_api_calls if "close" in c.expression]
    assert len(close_calls) >= 1
    assert close_calls[0].top_library == "ext", \
        f"self.client.close() should trace to ext, got {close_calls[0].top_library}"


# ── Test 8: mixed local + third-party alternatives ─────────────────────

def test_mixed_local_third_party_alternatives():
    code = ("import requests\n"
            "class Local:\n"
            "    pass\n"
            "def make(flag):\n"
            "    if flag:\n"
            "        return Local()\n"
            "    return requests.Session()\n"
            "make(False).get('x')\n")
    r = _run_code(code)
    get_calls = [c for c in r.all_api_calls if "get" in c.expression]
    assert len(get_calls) == 1
    assert get_calls[0].top_library == "requests"
    assert "requests" in r.library_usage
    assert "local" not in [k for k in r.library_usage.keys()]
    assert get_calls[0].confidence < 1.0, \
        f"Mixed alternatives should have confidence < 1.0, got {get_calls[0].confidence}"


# ── Test 9: v1 mode should still pass all existing tests ───────────────

# ── Phase 8C: decorator provenance ────────────────────────────────────

def test_decorated_function_call_is_local():
    """Decorated function call must be local, not the decorator's library."""
    code = ("import flask\n"
            "app = flask.Flask(__name__)\n"
            "@app.route('/')\n"
            "def index():\n"
            "    return 'hello'\n"
            "index()\n")
    r = _run_code(code)
    index_calls = [c for c in r.all_api_calls
                   if c.expression == "index()"]
    assert len(index_calls) == 1
    assert index_calls[0].top_library == "local", \
        f"index() should be local, got {index_calls[0].top_library}"


def test_decorator_evidence_in_provenance():
    """Decorator source must appear as kind='decorated_by' in provenance."""
    code = ("from dataclasses import dataclass\n"
            "@dataclass\n"
            "class User:\n"
            "    name: str\n"
            "User('Alice', 30)\n")
    r = _run_code(code)
    deco_provs = [p for p in r.all_symbol_provenance
                  if p.kind == "decorated_by"]
    assert len(deco_provs) >= 1, "Expected decorated_by provenance"
    assert deco_provs[0].top_library == "dataclasses", \
        f"Expected dataclasses, got {deco_provs[0].top_library}"
    # User() should still be local
    user_calls = [c for c in r.all_api_calls if "User" in c.expression]
    assert len(user_calls) >= 1
    assert user_calls[0].top_library == "local"


def test_decorator_expression_is_api_call():
    """Decorator expression itself must be an API call to the library."""
    code = ("import flask\n"
            "app = flask.Flask(__name__)\n"
            "@app.route('/')\n"
            "def index():\n"
            "    pass\n")
    r = _run_code(code)
    route_calls = [c for c in r.all_api_calls if "route" in c.expression]
    assert len(route_calls) >= 1
    assert route_calls[0].top_library == "flask", \
        f"app.route() should be flask, got {route_calls[0].top_library}"


def test_click_decorator_target_is_local():
    """click.command()/option() decorators must not make the command local."""
    code = ("import click\n"
            "@click.command()\n"
            "@click.option('--name')\n"
            "def hello(name):\n"
            "    click.echo(f'Hello {name}')\n"
            "hello()\n")
    r = _run_code(code)
    hello_calls = [c for c in r.all_api_calls
                   if c.expression == "hello()"]
    assert len(hello_calls) == 1
    assert hello_calls[0].top_library == "local", \
        f"hello() should be local, got {hello_calls[0].top_library}"
    echo_calls = [c for c in r.all_api_calls
                  if "echo" in c.expression]
    assert len(echo_calls) >= 1
    assert echo_calls[0].top_library == "click", \
        f"click.echo() should be click, got {echo_calls[0].top_library}"


def test_stacked_decorators_all_preserved():
    """Stacked decorators must all appear as decorated_by evidence."""
    code = ("def deco_a(f):\n"
            "    return f\n"
            "def deco_b(f):\n"
            "    return f\n"
            "@deco_a\n"
            "@deco_b\n"
            "def f():\n"
            "    pass\n"
            "f()\n")
    r = _run_code(code)
    deco_provs = [p for p in r.all_symbol_provenance
                  if p.kind == "decorated_by" and p.symbol == "f"]
    assert len(deco_provs) == 2, f"Expected 2 decorated_by, got {len(deco_provs)}"
    f_calls = [c for c in r.all_api_calls
               if c.expression == "f()"]
    assert len(f_calls) == 1
    assert f_calls[0].top_library == "local", \
        f"Decorated f() should be local, got {f_calls[0].top_library}"


# ── Phase 8C+: decorator identity and chaining ───────────────────────

def test_local_decorator_returns_thirdparty_decorator():
    """Local decorator that returns a third-party decorator must chain
    the decorated_by evidence to the third-party library."""
    code = ("import click\n"
            "def command(f):\n"
            "    return click.command()(f)\n"
            "@command\n"
            "def hello():\n"
            "    pass\n"
            "hello()\n")
    r = _run_code(code)
    hello_calls = [c for c in r.all_api_calls
                   if c.expression == "hello()"]
    assert len(hello_calls) == 1
    assert hello_calls[0].top_library == "local", \
        f"hello() should be local, got {hello_calls[0].top_library}"
    deco_provs = [p for p in r.all_symbol_provenance
                  if p.kind == "decorated_by" and p.symbol == "hello"]
    assert len(deco_provs) >= 1
    tops = {p.top_library for p in deco_provs}
    assert "click" in tops, f"Expected click in decorated_by, got {tops}"


def test_local_passthrough_decorator_is_local():
    """A passthrough decorator that returns f unchanged must not
    produce third-party decorated_by evidence."""
    code = ("def passthrough(f):\n"
            "    return f\n"
            "@passthrough\n"
            "def g():\n"
            "    pass\n"
            "g()\n")
    r = _run_code(code)
    deco_provs = [p for p in r.all_symbol_provenance
                  if p.kind == "decorated_by" and p.symbol == "g"]
    assert len(deco_provs) >= 1
    tops = {p.top_library for p in deco_provs}
    assert "click" not in tops
    assert "flask" not in tops


def test_apicall_decorated_by_field():
    """ApiCall.decorated_by must list decorator libraries for decorated
    local calls, matching by symbol name and file path."""
    code = ("import flask\n"
            "app = flask.Flask(__name__)\n"
            "@app.route('/')\n"
            "def index():\n"
            "    return 'hello'\n"
            "index()\n")
    r = _run_code(code)
    index_calls = [c for c in r.all_api_calls
                   if c.expression == "index()"]
    assert len(index_calls) == 1
    assert index_calls[0].top_library == "local"
    assert "flask" in index_calls[0].decorated_by, \
        f"decorated_by should contain flask, got {index_calls[0].decorated_by}"


def test_v1_still_works_for_local_functions():
    code = ("def helper():\n"
            "    pass\n"
            "helper()\n")
    r = _run_code(code, scope_model="v1")
    helper_calls = [c for c in r.all_api_calls if "helper" in c.expression]
    assert len(helper_calls) >= 1
    for c in helper_calls:
        assert c.top_library == "local", f"v1 helper() not local: {c.top_library}"


# ── Test 10: dotted import descendant must be library ─────────────────

def test_dotted_import_descendant_is_library():
    code = ("import gensim.models\n"
            "gensim.models.fasttext.FastText()\n")
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "FastText" in c.expression]
    assert len(calls) >= 1
    assert calls[0].top_library == "gensim", \
        f"Expected gensim, got {calls[0].top_library}"


def test_deep_dotted_import_descendant_is_library():
    code = ("import tornado.ioloop\n"
            "tornado.ioloop.IOLoop.instance()\n")
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "instance" in c.expression]
    assert len(calls) >= 1
    assert calls[0].top_library == "tornado", \
        f"Expected tornado, got {calls[0].top_library}"
