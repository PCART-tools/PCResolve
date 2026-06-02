## @package tests.test_regression_receiver_return_tracing
#  1.0.5 P1: receiver return tracing through cross-file factory functions.

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project


_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "regression_receiver_return_tracing")


def _analyze_subdir(name):
    """Analyze a sub-directory of the fixture with only the relevant files."""
    import tempfile, shutil
    src = os.path.join(_FIXTURE, name)
    with tempfile.TemporaryDirectory() as td:
        for f in os.listdir(_FIXTURE):
            if f.startswith(name) or f == 'factory.py':
                shutil.copy2(os.path.join(_FIXTURE, f), os.path.join(td, f))
        return analyze_project(td)


def test_from_import_factory():
    """from factory import create_app: app.test_client() → flask."""
    r = _analyze_subdir("main_from_import")
    app_calls = [c for c in r.all_api_calls
                 if "test_client" in c.func_name]
    assert app_calls, "app.test_client() not collected"
    for c in app_calls:
        assert c.top_library == "flask", \
            f"app.test_client should be flask, got {c.top_library}"
    get_calls = [c for c in r.all_api_calls
                 if "client.get" in c.func_name]
    for c in get_calls:
        assert c.top_library == "flask", \
            f"client.get should be flask, got {c.top_library}"


def test_module_import_factory():
    """import factory: app.test_client() → flask."""
    r = _analyze_subdir("main_module_import")
    app_calls = [c for c in r.all_api_calls
                 if "test_client" in c.func_name]
    assert app_calls, "app.test_client() not collected"
    for c in app_calls:
        assert c.top_library == "flask", \
            f"app.test_client should be flask, got {c.top_library}"
    get_calls = [c for c in r.all_api_calls
                 if "client.get" in c.func_name]
    assert get_calls, "client.get() not collected"
    for c in get_calls:
        assert c.top_library == "flask", \
            f"client.get should be flask, got {c.top_library}"


def test_alias_import_factory():
    """import factory as f: app.test_client() → flask."""
    r = _analyze_subdir("main_alias_import")
    app_calls = [c for c in r.all_api_calls
                 if "test_client" in c.func_name]
    assert app_calls, "app.test_client() not collected"
    for c in app_calls:
        assert c.top_library == "flask", \
            f"app.test_client should be flask, got {c.top_library}"
    get_calls = [c for c in r.all_api_calls
                 if "client.get" in c.func_name]
    assert get_calls, "client.get() not collected"
    assert all(c.top_library == "flask" for c in get_calls), \
        f"client.get should be flask: {[(c.top_library,) for c in get_calls]}"


def test_create_app_call_is_local():
    """create_app() call itself is local (calling a local function)."""
    r = analyze_project(os.path.join(_FIXTURE, "main_from_import.py"))
    app_calls = [c for c in r.all_api_calls
                 if c.func_name == "create_app"]
    for c in app_calls:
        assert c.top_library == "local", \
            f"create_app() must be local, got {c.top_library}"


def test_negative_strip_is_local():
    """s.strip() on parameter receiver must stay local."""
    r = analyze_project(_FIXTURE)
    strip_calls = [c for c in r.all_api_calls
                   if "strip" in c.func_name and "main_negative" in c.file_path]
    assert strip_calls, "s.strip() not collected"
    for c in strip_calls:
        assert c.top_library in ("local", "python"), \
            f"s.strip() must be local/python, got {c.top_library}"


def test_negative_replace_is_local():
    """experiment.replace() on parameter receiver must stay local."""
    r = analyze_project(_FIXTURE)
    replace_calls = [c for c in r.all_api_calls
                     if "replace" in c.func_name and "main_negative" in c.file_path]
    assert replace_calls, "experiment.replace() not collected"
    for c in replace_calls:
        assert c.top_library in ("local", "python"), \
            f"experiment.replace() must be local/python, got {c.top_library}"


def test_negative_astype_is_local():
    """Xr.astype() after arithmetic must stay local."""
    r = analyze_project(_FIXTURE)
    astype_calls = [c for c in r.all_api_calls
                    if "astype" in c.func_name and "main_negative" in c.file_path]
    assert astype_calls, "Xr.astype() not collected"
    for c in astype_calls:
        assert c.top_library in ("local", "python"), \
            f"Xr.astype() must be local/python, got {c.top_library}"
