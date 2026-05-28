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


def test_self_attr_dotted_callee_traces_to_library():
    """self.model.predict(X) where self.model = GPy.models.GPRegression(...)
    must trace the method call to GPy via instance_attrs."""
    code = ("import GPy\n"
            "class Model:\n"
            "    def __init__(self, X, y):\n"
            "        self.model = GPy.models.GPRegression(X, y)\n"
            "    def predict(self, X):\n"
            "        return self.model.predict(X)[0]\n"
            "m = Model([[1]], [[2]])\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "self.model.predict" in c.expression:
            assert c.top_library == "GPy", \
                f"self.model.predict should be GPy, got {c.top_library}"


def test_self_attr_alias_traces_to_library():
    """vor = self.voronoi; vor.add_points() must trace through self attr alias."""
    code = ("from scipy.spatial import Voronoi\n"
            "class NN:\n"
            "    def _fit(self, X):\n"
            "        self.voronoi = Voronoi(X)\n"
            "    def add_point(self, X, p):\n"
            "        vor = self.voronoi\n"
            "        vor.add_points(p)\n"
            "nn = NN()\n"
            "nn._fit([[1,2],[3,4]])\n"
            "nn.add_point([[1,2],[3,4]], [[5,6]])\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "vor.add" in c.expression:
            assert c.top_library == "scipy", \
                f"vor.add_points() should be scipy, got {c.top_library}"


def test_local_self_attr_subscript_not_misattributed():
    """Local self.attr with no external provenance must not be misattributed."""
    code = ("class Local:\n"
            "    def __init__(self):\n"
            "        self.data = [1,2,3]\n"
            "    def get(self, i):\n"
            "        x = self.data\n"
            "        return x[i]\n"
            "l = Local()\n"
            "l.get(0)\n")
    r = _run_code(code)
    for c in r.all_api_calls:
        if "x[" in c.expression:
            assert c.top_library in ("local", "python"), \
                f"local self attr subscript must not be third-party, got {c.top_library}"


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


# ── Assigned-result receiver provenance (7B-lite) ─────────────────────


def test_assigned_chained_call_result_inherits_library():
    """predictions = self.model.predict(X)[0].reshape(...); predictions.ravel() -> GPy."""
    code = (
        "import GPy\n"
        "class Wrapper:\n"
        "    def __init__(self, X, y):\n"
        "        self.model = GPy.models.GPRegression(X, y)\n"
        "    def run(self, X):\n"
        "        predictions = self.model.predict(X)[0].reshape(10, 10)\n"
        "        return predictions.ravel()\n"
        "Wrapper([[1]], [[2]]).run([[3]])\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "ravel" in c.expression]
    assert calls, "predictions.ravel() not collected"
    for c in calls:
        assert c.top_library == "GPy", \
            f"predictions.ravel() should be GPy, got {c.top_library} ({c.chain})"


def test_tuple_unpack_assigned_result_inherits_library():
    """a, b = self.model.predict(X); a.ravel() -> GPy."""
    code = (
        "import GPy\n"
        "class Wrapper:\n"
        "    def __init__(self, X, y):\n"
        "        self.model = GPy.models.GPRegression(X, y)\n"
        "    def run(self, X):\n"
        "        a, b = self.model.predict(X)\n"
        "        return a.ravel()\n"
        "Wrapper([[1]], [[2]]).run([[3]])\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "ravel" in c.expression]
    assert calls, "a.ravel() not collected"
    for c in calls:
        assert c.top_library == "GPy", \
            f"a.ravel() should be GPy, got {c.top_library} ({c.chain})"


def test_local_self_attr_not_polluted_to_library():
    """self.y = y (local param); (self.y * mask).sum() stays local."""
    code = (
        "def compute(self, mask):\n"
        "    return (self.y * mask).sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, ".sum() not collected"
    for c in calls:
        assert c.top_library == "local", \
            f"local self.y method should stay local, got {c.top_library}"


def test_non_import_backed_receiver_stays_local():
    """Local variable assigned from non-import source stays local."""
    code = (
        "class A:\n"
        "    def __init__(self):\n"
        "        self.data = [1, 2, 3]\n"
        "    def run(self):\n"
        "        x = self.data\n"
        "        return x.count(1)\n"
        "A().run()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "count" in c.expression]
    assert calls, "x.count() not collected"
    for c in calls:
        assert c.top_library == "local", \
            f"local x.count() should stay local, got {c.top_library}"


# ── Phase 7B-full gap tests (xfail — pending CallGraph return-object tracking) ─


def test_container_item_append_preserves_numpy_source():
    """lst.append(arr[0]) with numpy-sourced item traces to numpy (7B-full PR4)."""
    code = (
        "import numpy as np\n"
        "arr = np.array([1, 2, 3])\n"
        "lst = []\n"
        "lst.append(arr[0])\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "append" in c.expression]
    assert calls, "lst.append() not collected"
    for c in calls:
        assert c.top_library == "numpy", \
            f"append with numpy item should be numpy, got {c.top_library}"


def test_class_instance_method_not_confused_with_container():
    """b.add(arr) on local class stays local, not polluted to numpy."""
    code = (
        "import numpy as np\n"
        "class Bag:\n"
        "    def add(self, x):\n"
        "        return 1\n"
        "arr = np.array([1])\n"
        "b = Bag()\n"
        "b.add(arr)\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "add" in c.expression and "Bag" not in c.expression]
    assert calls, "b.add() not collected"
    for c in calls:
        assert c.top_library == "local", \
            f"b.add() should stay local, got {c.top_library} ({c.chain})"


def test_factory_returned_instance_method_traces_to_library():
    """kernel = kernels[dynamic_key]; kernel.K(X) traces to GPy (7B-full PR6)."""
    code = (
        "import GPy\n"
        "import numpy as np\n"
        "def make_kernel():\n"
        "    return GPy.kern.RBF(1)\n"
        "class Wrapper:\n"
        "    def run(self, X, key):\n"
        "        kernels = {'a': make_kernel()}\n"
        "        kernel = kernels[key]\n"
        "        return kernel.K(X)\n"
        "Wrapper().run(np.array([[1]]), 'a')\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "K" in c.expression]
    assert calls, "kernel.K() not collected"
    for c in calls:
        assert c.top_library == "GPy", \
            f"kernel.K() should be GPy, got {c.top_library} ({c.chain})"


def test_local_model_factory_method_call_traces_to_constructor_library():
    """model = NSGP(); model.fit(X, y) traces to sklearn via constructor self.gp attr (7B-full PR3)."""
    code = (
        "import numpy as np\n"
        "from sklearn.gaussian_process import GaussianProcessRegressor\n"
        "class NSGP:\n"
        "    def __init__(self):\n"
        "        self.gp = GaussianProcessRegressor()\n"
        "    def fit(self, X, y):\n"
        "        self.gp.fit(X, y)\n"
        "model = NSGP()\n"
        "model.fit([[1]], [1])\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "fit" in c.expression and "self.gp" not in c.expression]
    assert calls, "model.fit() not collected"
    for c in calls:
        assert c.top_library == "sklearn", \
            f"model.fit() should be sklearn, got {c.top_library}"


def test_method_result_object_keeps_library_for_followup_call():
    """y_new = model.predict(X); y_new.sum() traces to numpy via method return (7B-full PR5)."""
    code = (
        "import numpy as np\n"
        "class LocalModel:\n"
        "    def fit(self, X, y):\n"
        "        pass\n"
        "    def predict(self, X):\n"
        "        return np.array(X)\n"
        "model = LocalModel()\n"
        "y_new = model.predict([[1]])\n"
        "y_new.sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, "y_new.sum() not collected"
    for c in calls:
        assert c.top_library == "numpy", \
            f"y_new.sum() should be numpy, got {c.top_library}"


# ── Phase 7B-full PR1: call-graph fact integrity ───────────────────────


def _run_code_with_cg(code, scope_model="v2"):
    """Analyze code and return (result, project_cg)."""
    from pcresolve.cross_file import ProjectAnalyzer
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "main.py"), "w") as f:
            f.write(code)
        pa = ProjectAnalyzer(td, scope_model=scope_model)
        result = pa.analyze()
        return result, pa.project_cg


def test_class_summary_methods_are_populated():
    """ClassSummary.methods must be non-empty after class body visit."""
    code = (
        "class A:\n"
        "    def m(self):\n"
        "        pass\n"
        "A().m()\n"
    )
    _, cg = _run_code_with_cg(code)
    classes = cg.modules.get("main", None)
    assert classes is not None, "No module in project_cg"
    cs = classes.classes.get("A")
    assert cs is not None, "ClassSummary for A not found"
    assert len(cs.methods) >= 1, f"Expected A.methods non-empty, got {list(cs.methods.keys())}"
    assert "m" in cs.methods, f"Expected method 'm' in A.methods, got {list(cs.methods.keys())}"


def test_nested_function_qualname_is_outer_inner():
    """Nested function qualname must be outer.inner, not bare inner."""
    code = (
        "def outer():\n"
        "    def inner():\n"
        "        pass\n"
        "    inner()\n"
        "outer()\n"
    )
    _, cg = _run_code_with_cg(code)
    funcs = cg.modules.get("main", None)
    assert funcs is not None
    fs = funcs.functions.get("outer.inner")
    assert fs is not None, f"Nested function 'outer.inner' not found; keys={list(funcs.functions.keys())}"


def test_call_edge_has_caller_and_assigned_to():
    """CallEdge must record caller, assigned_to, and receiver_source."""
    code = (
        "class Wrapper:\n"
        "    def run(self):\n"
        "        import requests\n"
        "        x = requests.get('http://x')\n"
        "Wrapper().run()\n"
    )
    _, cg = _run_code_with_cg(code)
    edges = []
    for mcg in cg.modules.values():
        edges.extend(mcg.edges)
    assert len(edges) >= 1, "Expected at least one CallEdge"
    # Find the requests.get edge (callee base is "requests").
    get_edges = [e for e in edges
                 if str(e.callee) == "requests"
                 and e.caller.qualname != "<module>"]
    assert len(get_edges) >= 1, f"No edge with callee='requests'; edges={[(str(e.callee), e.caller.qualname) for e in edges]}"
    e = get_edges[0]
    assert e.caller.qualname != "", "CallEdge must have caller"
    assert e.assigned_to == ["x"], f"Expected assigned_to=['x'], got {e.assigned_to}"
    assert e.receiver_source is not None, "CallEdge must have receiver_source for obj.method()"
    assert "pos" in e.arg_sources, f"arg_sources should have 'pos' key, got {list(e.arg_sources.keys())}"
    assert "kw" in e.arg_sources, f"arg_sources should have 'kw' key"


def test_nested_call_does_not_steal_assigned_to():
    """result = outer(inner()): outer gets ['result'], inner gets []."""
    code = (
        "def inner():\n"
        "    return 42\n"
        "import numpy as np\n"
        "result = np.array(inner())\n"
    )
    _, cg = _run_code_with_cg(code)
    edges = []
    for mcg in cg.modules.values():
        edges.extend(mcg.edges)
    # np.array is the outer call — should have assigned_to
    outer_edges = [e for e in edges if str(e.callee) == "np"]
    assert len(outer_edges) >= 1, \
        f"No outer edge with callee='np'; edges={[(str(e.callee), e.assigned_to) for e in edges]}"
    outer = outer_edges[0]
    assert outer.assigned_to == ["result"], \
        f"outer np.array() should get assigned_to=['result'], got {outer.assigned_to}"
    # inner() is the nested argument call — should have empty assigned_to
    inner_edges = [e for e in edges if str(e.callee) == "local"]
    assert len(inner_edges) >= 1, \
        f"No inner edge; edges={[(str(e.callee), e.assigned_to, e.call_lineno) for e in edges]}"
    assert inner_edges[0].assigned_to == [], \
        f"inner() should get empty assigned_to, got {inner_edges[0].assigned_to}"


def test_import_backed_self_attr_in_class_attrs():
    """self.gp = GPRegression(...) should appear in ClassSummary.attrs."""
    code = (
        "from sklearn.gaussian_process import GaussianProcessRegressor\n"
        "class Model:\n"
        "    def __init__(self):\n"
        "        self.gp = GaussianProcessRegressor()\n"
        "Model()\n"
    )
    _, cg = _run_code_with_cg(code)
    cs = cg.modules.get("main", None)
    assert cs is not None
    model_cs = cs.classes.get("Model")
    assert model_cs is not None, f"Model not in classes; keys={list(cs.classes.keys())}"
    assert "self.gp" in model_cs.attrs, \
        f"self.gp should be in Model.attrs, got {list(model_cs.attrs.keys())}"


# ── Phase 7B-full PR2: function return-object tracking ──────────────────


def test_local_function_return_propagates_library_to_caller():
    """x = make_array(); x.sum() where make_array returns np.array -> numpy."""
    code = (
        "import numpy as np\n"
        "def make_array():\n"
        "    return np.array([1, 2, 3])\n"
        "x = make_array()\n"
        "x.sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, "x.sum() not collected"
    for c in calls:
        assert c.top_library == "numpy", \
            f"x.sum() should be numpy, got {c.top_library}"


def test_same_name_function_across_modules_not_polluted():
    """a.py: make_arr -> numpy; b.py: make_arr -> local list; b calls own, must not become numpy."""
    from pcresolve.cross_file import ProjectAnalyzer
    with tempfile.TemporaryDirectory() as td:
        # Module a: make_arr returns numpy array
        with open(os.path.join(td, "a.py"), "w") as f:
            f.write(
                "import numpy as np\n"
                "def make_arr():\n"
                "    return np.array([1, 2, 3])\n"
            )
        # Module b: make_arr returns local list; calls own make_arr
        with open(os.path.join(td, "b.py"), "w") as f:
            f.write(
                "def make_arr():\n"
                "    return [1, 2, 3]\n"
                "x = make_arr()\n"
                "x.count(1)\n"
            )
        pa = ProjectAnalyzer(td, scope_model="v2")
        result = pa.analyze()
        count_calls = [c for c in result.all_api_calls if "count" in c.expression]
        assert count_calls, "x.count() not collected in b.py"
        for c in count_calls:
            assert c.top_library != "numpy", \
                f"b.py x.count() must not be polluted to numpy, got {c.top_library} ({c.file_path})"
            assert c.top_library in ("local", "python", "unknown"), \
                f"b.py x.count() expected local/python/unknown, got {c.top_library}"


# ── Phase 7B-full PR3-fix: method-sensitive attr lookup ─────────────────


def test_unrelated_import_attr_not_leaked_to_method():
    """c.helper() stays local even if class has self.session = requests.Session()."""
    code = (
        "import requests\n"
        "class Client:\n"
        "    def __init__(self):\n"
        "        self.session = requests.Session()\n"
        "    def helper(self):\n"
        "        return 1\n"
        "c = Client()\n"
        "c.helper()\n"
    )
    r = _run_code(code)
    helper_calls = [c for c in r.all_api_calls if "helper" in c.expression]
    assert helper_calls, "c.helper() not collected"
    for c in helper_calls:
        assert c.top_library == "local", \
            f"c.helper() should stay local, got {c.top_library} ({c.chain})"


def test_method_gets_right_attr_not_wrong_one():
    """c.shape() gets numpy from self.arr, not requests from self.session."""
    code = (
        "import requests\n"
        "import numpy as np\n"
        "class C:\n"
        "    def __init__(self):\n"
        "        self.session = requests.Session()\n"
        "        self.arr = np.array([1])\n"
        "    def shape(self):\n"
        "        return self.arr.reshape(1, 1)\n"
        "c = C()\n"
        "c.shape()\n"
    )
    r = _run_code(code)
    shape_calls = [c for c in r.all_api_calls
                   if "shape" in c.expression and "reshape" not in c.expression]
    assert shape_calls, "c.shape() not collected"
    for c in shape_calls:
        assert c.top_library == "numpy", \
            f"c.shape() should be numpy, got {c.top_library} ({c.chain})"


# ── Phase 7B-full PR4-fix: arg-source must not leak through CallResult ──


def test_call_result_arg_source_not_leaked_to_return():
    """y = sink(arr); y.foo() stays local — args don't become return source."""
    code = (
        "import numpy as np\n"
        "def sink(x):\n"
        "    pass\n"
        "arr = np.array([1])\n"
        "y = sink(arr)\n"
        "y.foo()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "foo" in c.expression]
    assert calls, "y.foo() not collected"
    for c in calls:
        assert c.top_library == "local", \
            f"y.foo() should stay local, got {c.top_library} ({c.chain})"


def test_void_func_assigned_result_not_polluted():
    """obj = make(arr) where make returns None; obj.add() stays local."""
    code = (
        "import numpy as np\n"
        "def make(x):\n"
        "    return None\n"
        "arr = np.array([1])\n"
        "obj = make(arr)\n"
        "obj.add(1)\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "add" in c.expression and "make" not in c.expression]
    assert calls, "obj.add() not collected"
    for c in calls:
        assert c.top_library == "local", \
            f"obj.add() should stay local, got {c.top_library} ({c.chain})"


def test_same_named_method_across_classes_not_polluted():
    """A.get()->np, B.get()->1; b.get() result must not inherit A's numpy."""
    code = (
        "import numpy as np\n"
        "class A:\n"
        "    def get(self):\n"
        "        return np.array([1])\n"
        "class B:\n"
        "    def get(self):\n"
        "        return 1\n"
        "b = B()\n"
        "y = b.get()\n"
        "y.foo()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "foo" in c.expression]
    assert calls, "y.foo() not collected"
    for c in calls:
        assert c.top_library != "numpy", \
            f"y.foo() must not be polluted to numpy, got {c.top_library} ({c.chain})"


def test_multi_return_source_set_not_pick_first():
    """Single-third-party + literal return: converge to the sole candidate.

    When a method returns np.array in one branch and a literal in the
    other, the literal does not add a source to the SourceSet.  With
    only one candidate the resolver correctly converges to it.
    Multi-third-party returns (requests + numpy) are handled
    separately by test_make_chained_call_project_level."""
    code = (
        "import numpy as np\n"
        "class Model:\n"
        "    def predict(self, flag):\n"
        "        if flag:\n"
        "            return np.array([1])\n"
        "        return 1\n"
        "m = Model()\n"
        "y = m.predict(False)\n"
        "y.sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, "y.sum() not collected"
    for c in calls:
        assert c.top_library == "numpy", \
            f"v2 should resolve sole SourceSet candidate to numpy, got {c.top_library}"
        assert "numpy" in (getattr(c, "alternatives", []) or []), \
            f"alternatives should include numpy, got {getattr(c, 'alternatives', [])}"
        assert getattr(c, "reason", "") == "RETURN_PROPAGATION", \
            f"Expected RETURN_PROPAGATION, got {getattr(c, 'reason', '')}"
        assert "numpy" in r.library_usage, \
            "numpy missing from library_usage"


def test_cg_class_summary_method_returns_not_cross_class_polluted():
    """B.get returns must not inherit A.get's numpy return source."""
    code = (
        "import numpy as np\n"
        "class A:\n"
        "    def get(self):\n"
        "        return np.array([1])\n"
        "class B:\n"
        "    def get(self):\n"
        "        return 1\n"
    )
    _, cg = _run_code_with_cg(code)
    b_methods = cg.modules["main"].classes["B"].methods
    assert "get" in b_methods, f"B.get not in methods: {list(b_methods.keys())}"
    returns = b_methods["get"].returns
    if returns is not None:
        # Must not contain numpy from A.get's return
        returns_str = str(returns)
        assert "np" not in returns_str and "numpy" not in returns_str, \
            f"B.get returns must not leak A.get's numpy, got {returns!r}"


# ── Phase 7B-full PR6-fix: static key resolution + multi-candidate guard ──


def test_dict_static_key_resolves_exact_item():
    """items[key] with key='b' → local item, must not pick numpy from other key."""
    code = (
        "import numpy as np\n"
        "class Local:\n"
        "    def sum(self): return 1\n"
        "items = {'a': np.array([1]), 'b': Local()}\n"
        "key = 'b'\n"
        "obj = items[key]\n"
        "obj.sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, "obj.sum() not collected"
    for c in calls:
        assert c.top_library != "numpy", \
            f"obj.sum() must not be numpy when key='b' points to Local, got {c.top_library} ({c.chain})"


def test_dict_static_key_exact_import_match():
    """items[key] with key='b' → pandas, should get pandas."""
    code = (
        "import pandas as pd\n"
        "import numpy as np\n"
        "items = {'a': np.array([1]), 'b': pd.DataFrame()}\n"
        "key = 'b'\n"
        "obj = items[key]\n"
        "obj.sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, "obj.sum() not collected"
    for c in calls:
        assert c.top_library == "pandas", \
            f"obj.sum() should be pandas when key='b', got {c.top_library} ({c.chain})"


def test_multi_candidate_not_pick_arbitrary_primary():
    """items[input()] with numpy+pandas candidates: don't pick numpy as primary."""
    code = (
        "import numpy as np\n"
        "import pandas as pd\n"
        "items = {'a': np.array([1]), 'b': pd.DataFrame()}\n"
        "key = input()\n"
        "obj = items[key]\n"
        "obj.sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, "obj.sum() not collected"
    for c in calls:
        # Primary must not be arbitrarily set to a specific library
        assert c.top_library not in ("numpy", "pandas"), \
            f"obj.sum() primary must not be numpy/pandas arbitrarily, got {c.top_library}"


def test_multi_factory_same_library_dict_lookup_converges():
    """Two different factory functions both returning GPy: kernel.K() -> GPy."""
    code = (
        "import GPy\n"
        "import numpy as np\n"
        "def make_rbf():\n"
        "    return GPy.kern.RBF(1)\n"
        "def make_matern():\n"
        "    return GPy.kern.Matern32(1)\n"
        "kernels = {'a': make_rbf(), 'b': make_matern()}\n"
        "key = input()\n"
        "kernel = kernels[key]\n"
        "kernel.K([[1]])\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "K" in c.expression]
    assert calls, "kernel.K() not collected"
    for c in calls:
        assert c.top_library == "GPy", \
            f"kernel.K() should be GPy, got {c.top_library} ({c.chain})"


def test_factory_plus_direct_not_pick_arbitrary_primary():
    """make_arr()->numpy + pd.DataFrame() with dynamic key: not pandas/numpy."""
    code = (
        "import numpy as np\n"
        "import pandas as pd\n"
        "def make_arr():\n"
        "    return np.array([1])\n"
        "items = {'a': make_arr(), 'b': pd.DataFrame()}\n"
        "key = input()\n"
        "obj = items[key]\n"
        "obj.sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, "obj.sum() not collected"
    for c in calls:
        assert c.top_library not in ("numpy", "pandas"), \
            f"obj.sum() primary must not be numpy/pandas, got {c.top_library}"


def test_factory_gpy_plus_direct_not_pick_arbitrary_primary():
    """make_rbf()->GPy + pd.DataFrame() with dynamic key: not GPy/pandas."""
    code = (
        "import GPy\n"
        "import pandas as pd\n"
        "def make_rbf():\n"
        "    return GPy.kern.RBF(1)\n"
        "items = {'a': make_rbf(), 'b': pd.DataFrame()}\n"
        "key = input()\n"
        "obj = items[key]\n"
        "obj.sum()\n"
    )
    r = _run_code(code)
    calls = [c for c in r.all_api_calls if "sum" in c.expression]
    assert calls, "obj.sum() not collected"
    for c in calls:
        assert c.top_library not in ("GPy", "pandas"), \
            f"obj.sum() primary must not be GPy/pandas, got {c.top_library}"
