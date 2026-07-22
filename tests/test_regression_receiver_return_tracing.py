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


def test_uncalled_parameter_strip_is_unknown():
    """s.strip() on an unconstrained parameter must stay unknown."""
    r = analyze_project(_FIXTURE)
    strip_calls = [c for c in r.all_api_calls
                   if "strip" in c.func_name and "main_negative" in c.file_path]
    assert strip_calls, "s.strip() not collected"
    for c in strip_calls:
        assert c.top_library == "unknown", \
            f"s.strip() must be unknown, got {c.top_library}"


def test_uncalled_parameter_replace_is_unknown():
    """experiment.replace() on an unconstrained parameter stays unknown."""
    r = analyze_project(_FIXTURE)
    replace_calls = [c for c in r.all_api_calls
                     if c.func_name == "experiment.replace"
                     and "main_negative" in c.file_path]
    assert replace_calls, "experiment.replace() not collected"
    for c in replace_calls:
        assert c.top_library == "unknown", \
            f"experiment.replace() must be unknown, got {c.top_library}"


def test_unresolved_parameter_method_result_stays_unknown():
    """A chained call on an unresolved method result must stay unknown."""
    r = analyze_project(_FIXTURE)
    title_calls = [c for c in r.all_api_calls
                   if c.func_name.endswith(".title")
                   and "main_negative" in c.file_path]
    assert len(title_calls) == 1
    assert title_calls[0].top_library == "unknown"


def test_unresolved_astype_receiver_is_unknown():
    """Xr.astype() stays unknown without a bounded result-owner contract."""
    r = analyze_project(_FIXTURE)
    astype_calls = [c for c in r.all_api_calls
                    if "astype" in c.func_name and "main_negative" in c.file_path]
    assert astype_calls, "Xr.astype() not collected"
    for c in astype_calls:
        assert c.top_library == "unknown", \
            f"Xr.astype() must be unknown, got {c.top_library}"
