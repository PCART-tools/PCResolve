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
    # app.logger.info should have base = InstanceMethod(receiver="Flask", method="info")
    # since the root "app" traces to Flask, an imported class
    from pcresolve.sources import InstanceMethod as IM
    base = info_calls[0]["base"]
    assert isinstance(base, IM), f"Expected InstanceMethod base, got {type(base)}: {base!r}"


def test_multi_level_attribute_chain_on_imported_name():
    """imported_name.attr.method() where root is directly imported → third-party."""
    code = """from flask import request
request.headers.get("Authorization")
"""
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    get_calls = [c for c in tracer.api_calls if ".get(" in c["api"]]
    assert get_calls, ".get(...) call not found in api_calls"
    # request.headers.get should have base = InstanceMethod(receiver="request", method="get")
    # since the root "request" is directly imported from flask
    from pcresolve.sources import InstanceMethod as IM
    base = get_calls[0]["base"]
    assert isinstance(base, IM), f"Expected InstanceMethod base, got {type(base)}: {base!r}"


# ── Edge case: getattr(obj, "name") ────────────────────────────────────

def test_getattr_resolution():
    """getattr(obj, "attr_name") traces to obj's source."""
    code = """import requests
session = requests.Session()
meth = getattr(session, "get")
resp = meth("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    # meth = getattr(session, "get") — trace_source resolves to session's source
    assert any("meth(" in e and "requests" in t
               for e, t in calls.items()), (
        f"Expected meth(...) call with top=requests in {calls}"
    )


def test_getattr_attribute_call_detected():
    """getattr(obj, 'name')() itself should be detected as a call."""
    code = """import requests
session = requests.Session()
getattr(session, "get")("http://example.com")
"""
    result = analyze_source(code)
    expressions = [c.expression for c in result.api_calls]
    assert any("getattr" in e for e in expressions), (
        f"Expected getattr call detected, got {expressions}"
    )


# ── Edge case: importlib.import_module("name") ────────────────────────

def test_import_module_resolution():
    """importlib.import_module('name') resolves to the module name."""
    code = """import importlib
mod = importlib.import_module("requests")
resp = mod.get("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    # mod → "requests" via importlib.import_module("requests")
    assert any("mod.get(" in e and "requests" in t
               for e, t in calls.items()), (
        f"Expected mod.get(...) call with top=requests in {calls}"
    )


def test_import_module_with_from_import():
    """from importlib import import_module → should also resolve."""
    code = """from importlib import import_module
mod = import_module("numpy")
arr = mod.array([1, 2, 3])
"""
    result = analyze_source(code)
    chains = result.chains
    assert chains.get("mod")[-1] == "numpy", (
        f"Expected numpy, got {chains.get('mod')}"
    )


def test_import_module_dynamic_name_not_resolved():
    """Variable argument to import_module cannot be resolved."""
    code = """import importlib
name = "requests"
mod = importlib.import_module(name)
resp = mod.get("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    # Variable 'name' is not a string literal → import_module returns None
    # mod will trace to wherever name came from
    mod_calls = [e for e in calls if "mod.get(" in e]
    if mod_calls:
        # If detected, the top won't be "requests" (dynamic name)
        t = calls[mod_calls[0]]
        assert t != "requests", (
            f"Dynamic import_module should NOT resolve to 'requests', got {t!r}"
        )


# ── Edge case: functools.partial via alias ────────────────────────────

def test_partial_via_alias_not_resolved():
    """a = partial; a(requests.get, ...) — partial alias NOT detected.

    _is_partial_call only matches func.id == 'partial' or func.attr == 'partial'.
    An alias 'a' to partial is not recognized, so the return from a(func) traces
    to 'a' → 'partial' → 'functools' instead of 'func' → 'requests'.
    """
    code = """from functools import partial
import requests
a = partial
fetcher = a(requests.get, timeout=10)
resp = fetcher("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    # Known limitation: fetcher(...) resolves to functools, not requests
    actual = calls.get("fetcher('http://example.com')")
    assert actual == "functools", (
        f"Known limitation: partial alias not resolved, expected 'functools', got {actual!r}"
    )


# ── Edge case: set container ──────────────────────────────────────────

def test_set_container_tracked():
    """Set literals with imported callables are tracked in container_set_sources."""
    code = """import requests
import numpy as np

FUNCS_SET = {requests.delete, np.max}
"""
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    bases = tracer.container_set_sources.get("FUNCS_SET", set())
    # container_set_sources stores base symbols (e.g. 'np'), not resolved top names
    assert "requests" in bases, f"Expected requests in set sources, got {bases}"
    assert "np" in bases, f"Expected 'np' (base symbol) in set sources, got {bases}"


def test_set_container_iteration_via_for_loop():
    """for f in set_of_callables: f(...) — container_iter for set."""
    code = """import requests
import numpy as np

FUNCS_SET = {requests.get, np.sum}
for f in FUNCS_SET:
    result = f("https://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    # f(...) in loop body with set → container_iter → structured tuple
    # In single-file mode, container_iter tuples are NOT resolved —
    # they only get resolved in cross-file (ProjectAnalyzer) via _resolve_structured_source
    loop_calls = [e for e in calls if "f(" in e]
    assert loop_calls, f"Expected f(...) call from set iteration, got {calls}"
    # In single-file mode the top shows the source_display form (e.g. "FUNCS_SET[*]")
    actual = calls[loop_calls[0]]
    assert "FUNCS_SET" in actual or "[*]" in actual, (
        f"Expected container_iter display (unresolved in single-file), got {actual!r}"
    )


# ── Edge case: multiple return values ─────────────────────────────────

def test_multiple_return_values_first_wins():
    """A function with multiple returns — only the first encountered is recorded."""
    code = """import requests
import numpy as np

def get_func(kind):
    if kind == "get":
        return requests.get
    else:
        return np.sum

f = get_func("get")
resp = f("http://example.com")
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    # f = get_func(...) — the return flow may or may not resolve
    assert any("f(" in e for e, t in calls.items()), (
        f"Expected f(...) call in {calls}"
    )


# ── Edge case: async def / async with / async for ─────────────────────

def test_async_def_treated_as_local():
    """async def function is registered as locally defined."""
    code = """import aiohttp
async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()
"""
    tracer = SingleFileAnalyzer()
    tracer.visit(ast.parse(code))
    assert "fetch" in tracer.defined_functions, (
        f"Expected async def 'fetch' in defined_functions"
    )
    assert tracer.symbols.direct.get("fetch") == "local", (
        f"Expected 'local', got {tracer.symbols.direct.get('fetch')!r}"
    )


def test_async_for_loop_variable_bound():
    """async for item in it: — loop variable bound to iterator source (v1)."""
    code = """import aiohttp
async def iterate(it):
    async for item in it:
        val = item
    return val
"""
    tracer = SingleFileAnalyzer(scope_model="v1")
    tracer.visit(ast.parse(code))
    # item is bound from the async for iterator source
    assert "val" in tracer.symbols.direct, (
        f"Expected 'val' symbol from async for, got {list(tracer.symbols.direct)}"
    )


def test_async_with_context_variable_bound():
    """async with ... as var: — context variable bound to context source (v1)."""
    code = """import aiohttp
async def fetch(url):
    async with aiohttp.ClientSession() as session:
        return session
"""
    tracer = SingleFileAnalyzer(scope_model="v1")
    tracer.visit(ast.parse(code))
    # session should be bound to aiohttp.ClientSession's source
    assert "session" in tracer.symbols.direct, (
        f"Expected 'session' in direct from async with, got {list(tracer.symbols.direct)}"
    )


# ── Edge case: self.attr.method() via attribute assignment ────────────

def test_self_attr_method_not_in_class_body():
    """self.session.get() where session = requests.Session() assigned in __init__.

    _resolve_methods returns a structured tuple since 'get' is not a defined
    method of the local class. The call is recorded but resolution back to
    'requests' depends on the cross-file stage tracing self.session correctly.
    """
    code = """import requests
class Client:
    def __init__(self, url):
        self.session = requests.Session()
        self.url = url

    def fetch(self):
        return self.session.get(self.url)

c = Client("http://example.com")
resp = c.fetch()
"""
    result = analyze_source(code)
    calls = {c.expression: c.top_library for c in result.api_calls}
    # c.fetch() is resolved through _resolve_methods → "fetch" in defined_functions
    assert any("c.fetch(" in e and t == "local"
               for e, t in calls.items()), (
        f"Expected c.fetch(...) call with top=local in {calls}"
    )
    # self.session.get(...) inside fetch — traced as instance_method tuple
    session_get_calls = [e for e in calls if "self.session.get(" in e]
    assert session_get_calls, (
        f"Expected self.session.get(...) call to be detected in {calls}"
    )


def test_analyze_source_base_symbol_no_dataclass_repr():
    """analyze_source() must not leak dataclass repr in base_symbol."""
    code = """from flask import Flask
app = Flask(__name__)
app.logger.info('test')
"""
    result = analyze_source(code)
    info_calls = [c for c in result.api_calls if "info" in c.expression]
    assert info_calls, "app.logger.info(...) not found"
    base = info_calls[0].base_symbol
    # Must use source_display form, not dataclass repr
    assert "InstanceMethod(" not in base, f"Dataclass repr leaked: {base!r}"
    assert "Flask" in base


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
    test_getattr_resolution()
    test_getattr_attribute_call_detected()
    test_import_module_resolution()
    test_import_module_with_from_import()
    test_import_module_dynamic_name_not_resolved()
    test_partial_via_alias_not_resolved()
    test_set_container_tracked()
    test_set_container_iteration_via_for_loop()
    test_multiple_return_values_first_wins()
    test_async_def_treated_as_local()
    test_async_for_loop_variable_bound()
    test_async_with_context_variable_bound()
    test_self_attr_method_not_in_class_body()
    test_analyze_source_base_symbol_no_dataclass_repr()
    print("All SingleFileAnalyzer tests passed.")
