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


def test_decorated_method_call_decorated_by_known_limitation():
    """Decorated method calls like c.method() do not yet get
    decorated_by on ApiCall — class resolution needed (Phase 7B).
    SymbolProvenance retains the full evidence."""
    code = ("import flask\n"
            "app = flask.Flask(__name__)\n"
            "class C:\n"
            "    @app.route('/m')\n"
            "    def method(self):\n"
            "        pass\n"
            "c = C()\n"
            "c.method()\n")
    r = _run_code(code)
    # SymbolProvenance has the evidence
    deco_provs = [p for p in r.all_symbol_provenance
                  if p.kind == "decorated_by" and p.symbol == "method"]
    assert len(deco_provs) >= 1
    assert deco_provs[0].top_library == "flask"
    # Call is local (correct, not misclassified as flask)
    method_calls = [c for c in r.all_api_calls
                    if "method" in c.expression and c.expression != "app.route('/m')"]
    assert len(method_calls) >= 1
    assert method_calls[0].top_library == "local"


def test_decorated_by_method_fallback_not_leak_to_undecorated():
    """With exact-match-only lookup, method calls (A().method())
    have empty decorated_by — a known limitation until 7B class
    resolution.  SymbolProvenance retains evidence.  Neither
    A().method() nor B().method() gets decorated_by from the other."""
    code = ("import flask\n"
            "app = flask.Flask(__name__)\n"
            "class A:\n"
            "    @app.route('/m')\n"
            "    def method(self):\n"
            "        pass\n"
            "class B:\n"
            "    def method(self):\n"
            "        pass\n"
            "A().method()\n"
            "B().method()\n")
    r = _run_code(code)
    # SymbolProvenance has the evidence scoped correctly
    deco_provs = [p for p in r.all_symbol_provenance
                  if p.kind == "decorated_by" and p.symbol == "method"]
    assert len(deco_provs) == 1  # Only A.method is decorated
    assert deco_provs[0].scope_name == "A"
    assert deco_provs[0].top_library == "flask"
    # Neither call gets decorated_by (known limitation, exact match only)
    for c in r.all_api_calls:
        if "method" in c.expression and c.expression != "app.route('/m')":
            assert c.top_library == "local"
            assert c.decorated_by == [], \
                f"Method call decorated_by must be empty (known limitation)"


def test_decorated_by_scope_isolation():
    """Nested decorated handler must NOT pollute same-named module-level call."""
    code = ("import click\n"
            "def outer():\n"
            "    @click.command()\n"
            "    def handler():\n"
            "        pass\n"
            "def handler():\n"
            "    pass\n"
            "handler()\n")
    r = _run_code(code)
    handler_calls = [c for c in r.all_api_calls
                     if c.expression == "handler()"]
    assert len(handler_calls) >= 1
    assert handler_calls[0].top_library == "local"
    assert handler_calls[0].decorated_by == [], \
        f"module-level handler() must NOT have decorated_by, got {handler_calls[0].decorated_by}"


def test_module_level_decorator_not_leak_into_nested_scope():
    """Module-level @click.command handler must NOT decorate_by
    a same-named function defined inside a nested scope."""
    code = ("import click\n"
            "@click.command()\n"
            "def handler():\n"
            "    pass\n"
            "def outer():\n"
            "    def handler():\n"
            "        pass\n"
            "    handler()\n")
    r = _run_code(code)
    # Find the handler() call inside outer()
    for c in r.all_api_calls:
        if c.expression == "handler()" and c.top_library == "local":
            assert c.decorated_by == [], \
                f"nested handler() must NOT have decorated_by, got {c.decorated_by}"


def test_local_class_multi_instance_different_libraries():
    """Two instances of the same wrapper class with different external
    constructor args must resolve to their respective libraries."""
    code = ("import requests\n"
            "import httpx\n"
            "class Api:\n"
            "    def __init__(self, session):\n"
            "        self.session = session\n"
            "    def get(self, url):\n"
            "        return self.session.get(url)\n"
            "a = Api(requests.Session())\n"
            "b = Api(httpx.Client())\n"
            "a.get('x')\n"
            "b.get('y')\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "a.get" in c.expression:
            assert c.top_library == "requests", \
                f"a.get() should be requests, got {c.top_library}"
        if "b.get" in c.expression:
            assert c.top_library == "httpx", \
                f"b.get() should be httpx, got {c.top_library}"


# ── Phase 7B-lite PR 1: receiver provenance regression tests ────────────

def test_comprehension_iteration_receiver_traces_to_library():
    """v.mean() inside a comprehension over a locally-assigned DataFrame
    list must trace to pandas via the root scope binding."""
    code = ("import pandas as pd\n"
            "groups = [pd.DataFrame()]\n"
            "result = [v.mean() for v in groups]\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "mean" in c.expression:
            assert c.top_library == "pandas", \
                f"comprehension receiver should be pandas, got {c.top_library}"


def test_attribute_chain_receiver_uses_root_binding():
    """x.child.method() must trace root x through scope binding."""
    code = ("import ext\n"
            "class Wrapper:\n"
            "    def __init__(self, client):\n"
            "        self.c = client\n"
            "    def run(self):\n"
            "        return self.c.connect()\n"
            "def build():\n"
            "    w = Wrapper(ext.Client())\n"
            "    return w.run()\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "connect" in c.expression:
            assert c.top_library == "ext", \
                f"attribute-chain receiver should trace to ext, got {c.top_library}"


def test_local_object_attribute_chain_not_misattributed():
    """Local object attribute must not be misattributed to a third-party."""
    code = ("class Local:\n"
            "    def method(self): pass\n"
            "def f(x):\n"
            "    x.child.method()\n"
            "f(Local())\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "method" in c.expression:
            assert c.top_library == "local", \
                f"local object method must be local, got {c.top_library}"


# ── Phase 7B hardening (4 categories) ────────────────────────────────────
#  (1) multi-instance: test_local_class_multi_instance_different_libraries
#  (2) alias receiver:  test_7b_alias_receiver_follows_to_external
#  (3) factory local:   test_7b_factory_returned_instance_stays_local
#  (4) pure-local:      test_7b_pure_local_method_stays_local

def test_7b_alias_receiver_follows_to_external():
    """(2) alias receiver — c = b; c.get(...) where b = Api(httpx.Client())
    must still trace to httpx through the alias."""
    code = ("import requests\n"
            "import httpx\n"
            "class Api:\n"
            "    def __init__(self, session):\n"
            "        self.session = session\n"
            "    def get(self, url):\n"
            "        return self.session.get(url)\n"
            "a = Api(requests.Session())\n"
            "b = Api(httpx.Client())\n"
            "c = b\n"
            "c.get('z')\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "c.get" in c.expression:
            assert c.top_library == "httpx", \
                f"c.get() via alias should be httpx, got {c.top_library}"


def test_7b_factory_returned_instance_stays_local():
    """Factory-returned class instances (c = make(httpx.Client()))
    must stay local — no constructor call-site match available."""
    code = ("import requests\n"
            "import httpx\n"
            "class Api:\n"
            "    def __init__(self, session):\n"
            "        self.session = session\n"
            "    def get(self, url):\n"
            "        return self.session.get(url)\n"
            "def make(session):\n"
            "    return Api(session)\n"
            "c = make(httpx.Client())\n"
            "c.get('z')\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "c.get" in c.expression:
            assert c.top_library == "local", \
                f"factory c.get() should be local, got {c.top_library}"


def test_7b_pure_local_method_stays_local():
    """A class with no external constructor args must keep all
    method calls as local."""
    code = ("class Calc:\n"
            "    def __init__(self):\n"
            "        self.value = 0\n"
            "    def add(self, x):\n"
            "        self.value += x\n"
            "        return self.value\n"
            "c = Calc()\n"
            "c.add(5)\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "add" in c.expression:
            assert c.top_library == "local", \
                f"Calc.add() should be local, got {c.top_library}"


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
