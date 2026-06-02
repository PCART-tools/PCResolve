## @package tests.test_regression_receiver_object_ownership
#  1.0.5 P1: receiver object ownership — constructor, alias, factory.

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project


_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "regression_receiver_object_ownership")


def _analyze_fixture():
    return analyze_project(_FIXTURE)


def _call_map():
    """Return {expression: ApiCall} dict for main.py calls."""
    r = _analyze_fixture()
    return {c.expression: c for c in r.all_api_calls
            if 'main' in c.file_path}


def test_constructor_binding():
    """s = Session(); s.get() → requests, resolved_func=requests.Session.get."""
    calls = _call_map()
    c = calls.get("s1.get('/')")
    assert c is not None, "s1.get('/') not found"
    assert c.top_library == "requests"
    assert c.resolved_func == "requests.Session.get", f"got {c.resolved_func}"


def test_alias_constructor_binding():
    """import requests as rq; s = rq.Session(); s.get() → requests."""
    calls = _call_map()
    c = calls.get("s2.get('/')")
    assert c is not None
    assert c.top_library == "requests"
    assert c.resolved_func == "requests.Session.get", f"got {c.resolved_func}"


def test_flask_constructor_method():
    """from flask import Flask; app.test_client() → flask.Flask.test_client."""
    calls = _call_map()
    tc = calls.get("app.test_client()")
    assert tc is not None
    assert tc.top_library == "flask"
    assert tc.resolved_func == "flask.Flask.test_client", f"got {tc.resolved_func}"
    rt = calls.get("app.route('/')")
    assert rt is not None
    assert rt.top_library == "flask"
    assert rt.resolved_func == "flask.Flask.route", f"got {rt.resolved_func}"


def test_local_factory_return():
    """Local def returns Session(); s.get() → requests."""
    calls = _call_map()
    c = calls.get("s4.get('/')")
    assert c is not None
    assert c.top_library == "requests"
    # Factory returns don't preserve class info; resolved_func is conservative.
    assert c.resolved_func in ("requests.get",), f"got {c.resolved_func}"


def test_cross_file_factory_alias():
    """from factory import make_session as cross_make; s.get() → requests."""
    calls = _call_map()
    c = calls.get("s6.get('/')")
    assert c is not None
    assert c.top_library == "requests"
    # Alias factory return: resolved_func stays as the original expression
    # while top_library carries the ownership.
    assert c.resolved_func in ("s6.get", "requests.get"), \
        f"got {c.resolved_func}"


def test_cross_file_factory_direct():
    """from factory import make_session; s.get() → requests."""
    calls = _call_map()
    c = calls.get("s6b.get('/')")
    assert c is not None
    assert c.top_library == "requests"
    assert c.resolved_func in ("requests.get",), f"got {c.resolved_func}"


def test_make_session_is_local():
    """make_session() call itself is local."""
    calls = _call_map()
    for expr in ("make_session()",):
        c = calls.get(expr)
        if c:
            assert c.top_library == "local", f"{expr} must be local, got {c.top_library}"


def test_cross_make_is_local():
    """cross_make() call itself is local."""
    calls = _call_map()
    cross_calls = [c for c in calls.values() if c.func_name == "cross_make"]
    for c in cross_calls:
        assert c.top_library == "local", \
            f"cross_make() must be local, got {c.top_library}"


def test_negative_strip_stays_local():
    """text.strip() on local string must stay local/python."""
    r = _analyze_fixture()
    calls = {c.expression: c.top_library for c in r.all_api_calls
             if 'main' in c.file_path}
    assert calls.get("text.strip()") in ("local", "python"), calls
    assert calls.get("text.replace('h', 'H')") in ("local", "python"), calls


def test_negative_reassign_stays_local():
    """s = Session(); s = str; s.strip() must stay local/python."""
    r = _analyze_fixture()
    calls = {c.expression: c.top_library for c in r.all_api_calls
             if 'main' in c.file_path}
    assert calls.get("s_guard.strip()") in ("local", "python"), calls
