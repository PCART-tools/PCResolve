## @package tests.test_api_classification
#  Integration tests verifying API call classification rules.
#
#  Core principle: a call is a third-party API call iff inspect.getmodule()
#  would return a third-party library module. Locally defined functions /
#  methods are always "local" regardless of what third-party APIs they
#  use internally.

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pcresolve import analyze_project

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
FIXTURE = os.path.join(FIXTURES, "api_classification")


def _call_tops(result):
    """Return a dict of expression -> top_library for easy assertion."""
    return {c.expression: c.top_library for c in result.all_api_calls}


def _file_calls(result, filename):
    """Return a dict of expression -> top_library for a specific file."""
    for f in result.files:
        if f.file_path.endswith(filename):
            return {c.expression: c.top_library for c in f.api_calls}
    return {}


def test_local_function_is_local():
    """Calling a locally defined function is classified as local."""
    result = analyze_project(FIXTURE)
    main_tops = _file_calls(result, "main.py")
    assert main_tops.get("fetch_data('http://a.com')") == "local"


def test_alias_to_thirdparty_is_thirdparty():
    """Function alias (f = requests.get) preserves third-party identity."""
    result = analyze_project(FIXTURE)
    main_tops = _file_calls(result, "main.py")
    assert main_tops.get("get_alias('http://b.com')") == "requests"


def test_partial_of_thirdparty_is_thirdparty():
    """functools.partial of a third-party function is still third-party."""
    result = analyze_project(FIXTURE)
    main_tops = _file_calls(result, "main.py")
    assert main_tops.get("fetcher('http://c.com')") == "requests"


def test_local_class_method_is_local():
    """Calling a locally defined method is local."""
    result = analyze_project(FIXTURE)
    main_tops = _file_calls(result, "main.py")
    # client.get('http://d.com') — get is defined in LocalClient body
    keys = [k for k in main_tops if "client.get" in k]
    assert keys, "Expected client.get(...) call not found"
    assert main_tops[keys[0]] == "local"


def test_method_inherited_from_local_base_is_local():
    """Method inherited from a local parent class is still local."""
    result = analyze_project(FIXTURE)
    main_tops = _file_calls(result, "main.py")
    keys = [k for k in main_tops if "m_client.get" in k]
    assert keys, "Expected m_client.get(...) call not found"
    assert main_tops[keys[0]] == "local"


def test_method_inherited_from_thirdparty_base_is_thirdparty():
    """Method inherited from a third-party base class is third-party."""
    result = analyze_project(FIXTURE)
    main_tops = _file_calls(result, "main.py")
    keys = [k for k in main_tops if "tp.get" in k]
    assert keys, "Expected tp.get(...) call not found"
    assert main_tops[keys[0]] == "requests"


def test_nested_local_call_is_local():
    """Calling a local function that calls another local function is local."""
    result = analyze_project(FIXTURE)
    main_tops = _file_calls(result, "main.py")
    assert main_tops.get("wrapper('http://f.com')") == "local"


def test_symbol_chain_follows_return_flow_cross_file():
    """Symbol chain for an assignment must follow return_sources across files.

    a.py:  from b import fetch; result = fetch(1)
    b.py:  def fetch(id): return requests.get(...)

    result's value comes from fetch() → requests.get() → requests.
    The symbol chain for 'result' must end with 'requests'.
    """
    result = analyze_project(os.path.join(FIXTURES, "test2"))
    for f in result.files:
        if f.file_path.endswith("a.py"):
            chain = f.chains.get("result")
            assert chain, f"result not found in chains of a.py"
            assert chain[-1] == "requests", (
                f"Chain should end with 'requests' (data flow), got {chain}"
            )
            return
    assert False, "a.py not found in analysis results"


def test_call_to_local_cross_file_function_is_local():
    """Call to imported local function is classified as local.
    Call classification uses definition origin, not data flow."""
    result = analyze_project(os.path.join(FIXTURES, "test2"))
    calls = _file_calls(result, "a.py")
    fetch_calls = [e for e in calls if "fetch(" in e]
    assert fetch_calls, "fetch(...) call not found in a.py"
    assert calls[fetch_calls[0]] == "local", (
        f"Expected local, got {calls[fetch_calls[0]]}"
    )


def test_result_symbol_shows_correct_top_source():
    """FileAnalysis.symbols for 'result' must be 'requests' (data flow)."""
    result = analyze_project(os.path.join(FIXTURES, "test2"))
    for f in result.files:
        if f.file_path.endswith("a.py"):
            assert f.symbols.get("result") == "requests", (
                f"Expected requests, got {f.symbols.get('result')}"
            )
            return
    assert False, "a.py not found in analysis results"


def test_direct_thirdparty_calls_in_function_bodies_are_still_thirdparty():
    """requests.get(url) inside a def body is still a third-party API call."""
    result = analyze_project(FIXTURE)
    all_tops = _call_tops(result)
    # At least one requests.get call should appear as third-party
    thirdparty_gets = [
        expr for expr, top in all_tops.items()
        if "requests.get" in expr and top == "requests"
    ]
    assert thirdparty_gets, (
        f"Expected requests.get(...) calls in output with top=requests, "
        f"got: {all_tops}"
    )


def test_multi_level_attribute_chain_classified_as_thirdparty():
    """app.logger.info(...) where app is a Flask instance → flask."""
    result = analyze_project(os.path.join(FIXTURES, "test_projects", "flask2"))
    for f in result.files:
        if f.file_path.endswith("app.py"):
            for c in f.api_calls:
                if "app.logger.info" in c.expression:
                    assert c.top_library == "flask", (
                        f"Expected flask, got {c.top_library}"
                    )
                    return
    assert False, "app.logger.info(...) call not found"


def test_multi_level_attribute_chain_on_imported_name_is_thirdparty():
    """request.headers.get(...) / request.json.get(...) where request is
    directly imported from flask → flask."""
    result = analyze_project(os.path.join(FIXTURES, "test_projects", "flask2"))
    for f in result.files:
        if f.file_path.endswith("app.py"):
            for c in f.api_calls:
                if "request." in c.expression and ".get(" in c.expression:
                    assert c.top_library == "flask", (
                        f"Expected flask, got {c.top_library} for {c.expression[:60]}"
                    )
