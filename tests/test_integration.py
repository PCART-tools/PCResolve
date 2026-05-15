## @package tests.test_integration
#  Integration tests using existing fixture projects.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project


FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def test_tests1():
    result = analyze_project(os.path.join(FIXTURES, "tests1"))
    assert len(result.files) == 2
    assert len(result.all_api_calls) == 3
    tops = {c.expression: c.top_library for c in result.all_api_calls}
    assert "requests" in tops.values()
    assert "numpy" in tops.values()


def test_tests2():
    result = analyze_project(os.path.join(FIXTURES, "tests2"))
    assert len(result.files) == 4
    tops = {c.top_library for c in result.all_api_calls}
    assert "requests" in tops
    assert "numpy" in tops
    assert "pandas" in tops


def test_tests3():
    result = analyze_project(os.path.join(FIXTURES, "tests3"))
    assert len(result.files) == 3
    tops = {c.top_library for c in result.all_api_calls}
    assert "requests" in tops or "numpy" in tops


def test_all_files_have_module_names():
    result = analyze_project(os.path.join(FIXTURES, "tests2"))
    for f in result.files:
        assert f.module_name, f"File {f.file_path} has no module name"
        assert f.file_path, f"File has no path"


def test_no_calls_on_empty_project(tmp_path):
    (tmp_path / "empty.py").write_text("x = 1\ny = x + 2")
    result = analyze_project(str(tmp_path))
    assert len(result.files) == 1
    assert len(result.all_api_calls) == 0


# ── tests4: cross-file assignment chain ──────────────────────────────

def test_tests4_cross_file_assignment_chain():
    """Assignment of module attributes in a.py, re-used in b.py."""
    result = analyze_project(os.path.join(FIXTURES, "tests4"))
    tops = {c.top_library for c in result.all_api_calls}
    assert "numpy" in tops
    assert "pandas" in tops


# ── tests5: dict subscript, closures ──────────────────────────────────

def test_tests5_dict_subscript_and_closure():
    """Dict-lookup callables and closure-wrapped API calls."""
    result = analyze_project(os.path.join(FIXTURES, "tests5"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    assert tops_by_expr.get("http_get('https://api.example.com/users/1')") == "requests"
    assert tops_by_expr.get("func(url)") == "requests"
    # make_client(...) is a local function returning a closure
    assert tops_by_expr.get("get_user('/users/1')") == "local"


# ── tests6: cross-file closure ────────────────────────────────────────

def test_tests6_cross_file_closure():
    """Closure imported from another module; call site classification."""
    result = analyze_project(os.path.join(FIXTURES, "tests6"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    assert tops_by_expr.get("session.get(base_url + path)") == "requests"
    assert tops_by_expr.get("func(url)") == "requests"
    # get_user is a locally-defined closure → local
    assert tops_by_expr.get("get_user('/users/1')") == "local"


# ── tests7: dict subscript single file ────────────────────────────────

def test_tests7_dict_subscript_single_file():
    """func = d[key] where d contains imported callables."""
    result = analyze_project(os.path.join(FIXTURES, "tests7"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    assert tops_by_expr.get("func_get('https://example.com')") == "requests"
    assert tops_by_expr.get("func_post('https://example.com')") == "requests"
    assert tops_by_expr.get("func_pool()") == "pandas"


# ── tests8: partial and lambda ────────────────────────────────────────

def test_tests8_partial_and_lambda():
    """functools.partial and lambda wrapping of third-party functions."""
    result = analyze_project(os.path.join(FIXTURES, "tests8"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    # direct partial(requests.post, ...) → requests
    assert tops_by_expr.get("post_data('https://api.example.com/data', json={'key': 'value'})") == "requests"
    # direct partial(np.sqrt) → numpy
    assert tops_by_expr.get("sqrt_arr([1, 4, 9])") == "numpy"
    # lambda wrapping requests.get → requests
    assert tops_by_expr.get("http_get('https://example.com')") == "requests"
    # lambda wrapping np.sum → numpy
    assert tops_by_expr.get("array_sum([1, 2, 3, 4, 5])") == "numpy"
    # lambda wrapping Session().get → requests
    assert tops_by_expr.get("make_request('https://example.com/api')") == "requests"


def test_tests8_partial_via_alias_known_issue():
    """a = partial; a(requests.get, ...) → currently resolves as functools.

    This is a known limitation: _is_partial_call only matches func.id == 'partial'
    or func.attr == 'partial', so an alias to partial is not recognized.
    The expected ideal result would be 'requests'.
    """
    result = analyze_project(os.path.join(FIXTURES, "tests8"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    # Known failure: get_json(...) resolves to functools instead of requests
    actual = tops_by_expr.get("get_json('https://api.example.com/users/1')")
    assert actual == "functools", (
        f"Documented limitation: expected 'functools' (partial alias not resolved), got {actual!r}"
    )


# ── tests9: container subscript cross-file ────────────────────────────

def test_tests9_container_subscript_cross_file():
    """List/tuple subscript and negative index across module boundary."""
    result = analyze_project(os.path.join(FIXTURES, "tests9"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    assert tops_by_expr.get("f0('https://example.com')") == "requests"
    assert tops_by_expr.get("f1([1, 2, 3])") == "numpy"
    assert tops_by_expr.get("f2('https://example.com', data=b'hi')") == "requests"
    # negative indices
    assert tops_by_expr.get("fa('https://example.com')") == "requests"
    assert tops_by_expr.get("fb('https://example.com')") == "numpy"
    # tuple subscript
    assert tops_by_expr.get("t0([1, 2, 3])") == "numpy"
    assert tops_by_expr.get("t1('https://example.com')") == "requests"


# ── tests10: class method and return tracking ─────────────────────────

def test_tests10_class_method_and_return():
    """Class methods on local classes, return-flow, and chained calls."""
    result = analyze_project(os.path.join(FIXTURES, "tests10"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    # local class instantiation
    assert tops_by_expr.get("UserClient('https://api.example.com')") == "local"
    # method defined on local class → local
    assert tops_by_expr.get("client.get_user(1)") == "local"
    # numpy calls in the module body
    assert tops_by_expr.get("np.array([1, 2, 3])") == "numpy"
    # return-flow: _returns_requests_get → calls traced to local function
    assert tops_by_expr.get("_returns_requests_get()") == "local"


def test_tests10_self_attr_method_known_issue():
    """self.session.get(url) where session=requests.Session() → currently 'local'.

    This is a known limitation: _resolve_methods finds self.session.get as an
    instance method on the local class. Since 'get' is not in the class's method
    list, it generates a structured tuple. The structured tuple is resolved back
    to 'local' because the receiver class is locally defined, even though
    the actual object providing the 'get' method is requests.Session.
    """
    result = analyze_project(os.path.join(FIXTURES, "tests10"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    actual = tops_by_expr.get("self.session.get(url)")
    assert actual == "local", (
        f"Documented limitation: expected 'local' (self.session not traced), got {actual!r}"
    )


# ── tests11: class inheritance ────────────────────────────────────────

def test_tests11_class_inheritance():
    """Method resolution through class inheritance with external base."""
    result = analyze_project(os.path.join(FIXTURES, "tests11"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    assert tops_by_expr.get("Class1()") == "local"


def test_tests11_inherited_method_source_known_issue():
    """o1.foo1() where Class1(Class2=Session, Class3, Class4).

    foo1 is defined in Class3 and Class4 (local), but PCResolve stops at Class2
    (Session from requests) because it's the first base that traces to an external
    library. The result is 'requests' although foo1 is actually local.
    """
    result = analyze_project(os.path.join(FIXTURES, "tests11"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    actual = tops_by_expr.get("o1.foo1()")
    assert actual == "requests", (
        f"Documented limitation: expected 'requests' (method source misattribution), got {actual!r}"
    )


# ── tests12: decorators ───────────────────────────────────────────────

def test_tests12_decorators():
    """Flask route decorator and custom function/class decorators."""
    result = analyze_project(os.path.join(FIXTURES, "tests12"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    # Flask route decorator: app.route(...)
    assert tops_by_expr.get("app.route('/hello')") == "flask"
    # Flask(...) → flask
    assert tops_by_expr.get("Flask(__name__)") == "flask"
    # requests calls inside decorator body are traced
    assert tops_by_expr.get("requests.get('https://example.com/ping')") == "requests"
    # decorated function is local
    assert tops_by_expr.get("handle_response('https://example.com')") == "local"
    # decorated class is local
    assert tops_by_expr.get("DecoratedClient()") == "local"


# ── tests13: with-statement and for-loop ──────────────────────────────

def test_tests13_with_statement():
    """with requests.Session() as session: session.get(...) traced."""
    result = analyze_project(os.path.join(FIXTURES, "tests13"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    assert tops_by_expr.get("session.get('https://example.com')") == "requests"
    # async with aiohttp.ClientSession() as client: client.get(...)
    assert tops_by_expr.get("client.get('https://example.com')") == "aiohttp"


def test_tests13_for_loop_container_iteration():
    """for f in FUNCS: f(...) — container iteration with mixed candidates."""
    result = analyze_project(os.path.join(FIXTURES, "tests13"))
    tops_by_expr = {c.expression: c.top_library for c in result.all_api_calls}
    # f('https://example.com') in the loop body: FUNCS = [requests.get, np.sum]
    # both candidates merged → "[requests,numpy]"
    actual = tops_by_expr.get("f('https://example.com')")
    assert actual in ("[requests,numpy]", "[numpy,requests]"), (
        f"Expected merged container candidates, got {actual!r}"
    )


if __name__ == "__main__":
    test_tests1()
    test_tests2()
    test_tests3()
    test_all_files_have_module_names()
    test_tests4_cross_file_assignment_chain()
    test_tests5_dict_subscript_and_closure()
    test_tests6_cross_file_closure()
    test_tests7_dict_subscript_single_file()
    test_tests8_partial_and_lambda()
    test_tests8_partial_via_alias_known_issue()
    test_tests9_container_subscript_cross_file()
    test_tests10_class_method_and_return()
    test_tests10_self_attr_method_known_issue()
    test_tests11_class_inheritance()
    test_tests11_inherited_method_source_known_issue()
    test_tests12_decorators()
    test_tests13_with_statement()
    test_tests13_for_loop_container_iteration()
    print("Integration tests passed.")
    print("Note: test_no_calls_on_empty_project requires pytest tmp_path.")
    print("Run full suite: python -m pytest tests/ -v")
