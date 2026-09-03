## @package tests.test_regression_import_wildcard_receiver_ownership
#  Preserve import-backed ownership when a module also has a local wildcard.

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pcresolve import analyze_project


_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "import_wildcard_receiver_ownership")


def _call_map():
    result = analyze_project(_FIXTURE)
    return {call.expression: call for call in result.all_api_calls
            if call.file_path.endswith("main.py")}


def test_external_class_method_survives_local_wildcard():
    calls = _call_map()
    call = calls["ViewClient.connectToDeviceOrExit()"]
    assert call.top_library == "com"


def test_external_constructor_survives_local_wildcard():
    calls = _call_map()
    call = calls["ViewClient(device, serial)"]
    assert call.top_library == "com"


def test_external_instance_method_survives_local_wildcard():
    calls = _call_map()
    call = calls["client.dump()"]
    assert call.top_library == "com"


def test_local_wildcard_class_remains_local():
    calls = _call_map()
    assert calls["LocalClient()"].top_library == "local"
    assert calls["local_client.run()"].top_library == "local"


def test_explicit_dotted_local_import_remains_local():
    calls = _call_map()
    assert calls["LocalDeepClient()"].top_library == "local"
    assert calls["local_deep_client.run()"].top_library == "local"


def test_simple_external_import_survives_local_wildcard():
    calls = _call_map()
    assert calls["Session()"].top_library == "requests"
    session_methods = [call for call in calls.values()
                       if call.func_name == "session.get"]
    assert len(session_methods) == 1
    assert session_methods[0].top_library == "requests"


def test_external_wildcard_does_not_override_python_literal_method():
    result = analyze_project(_FIXTURE)
    calls = [call for call in result.all_api_calls
             if call.file_path.endswith("external_wildcard.py")]
    assert len(calls) == 1
    assert calls[0].func_name.endswith(".join")
    assert calls[0].top_library == "python"
