## @package tests.test_regression_context_manager_receiver
#  1.0.5 Task C: context manager receiver ownership.

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project


_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "regression_context_manager_receiver")


def _call_map():
    r = analyze_project(_FIXTURE)
    return {c.expression: c for c in r.all_api_calls}


def test_direct_constructor_cm():
    """with Session() as s: s.get() → requests."""
    calls = _call_map()
    c = calls.get("s1.get('/')")
    assert c is not None
    assert c.top_library == "requests"


def test_alias_constructor_cm():
    """with rq.Session() as s: s.post() → requests."""
    calls = _call_map()
    c = calls.get("s2.post('/')")
    assert c is not None
    assert c.top_library == "requests"


def test_module_constructor_cm():
    """with requests.Session() as s: s.get() → requests."""
    calls = _call_map()
    c = calls.get("s3.get('/')")
    assert c is not None
    assert c.top_library == "requests"


def test_local_factory_cm():
    """with make_session() as s: s.get() → requests."""
    calls = _call_map()
    c = calls.get("s4.get('/')")
    assert c is not None
    assert c.top_library == "requests"


def test_open_not_requests():
    """with open(...) as f: f.read() must stay python."""
    calls = _call_map()
    c = calls.get("f.read()")
    assert c is not None
    assert c.top_library == "python"


def test_local_cm_not_guessed():
    """with LocalCM() as obj: obj.run() must stay local."""
    calls = _call_map()
    c = calls.get("obj.run()")
    assert c is not None
    assert c.top_library == "local"


def test_cross_file_factory_chain_cm():
    """with create_app().test_client() as client: client.get() → flask."""
    calls = _call_map()
    c = calls.get("client.get('/')")
    assert c is not None, "client.get('/') not collected"
    assert c.top_library == "flask", f"got {c.top_library}"
