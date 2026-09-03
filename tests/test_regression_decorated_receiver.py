## @package tests.test_regression_decorated_receiver
#  1.0.5 P2: decorated callable receiver evidence.

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from pcresolve import analyze_project


_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                        "regression_decorated_receiver")


def test_click_main_decorated_by():
    """hello.main() top=local, decorated_by contains click."""
    r = analyze_project(_FIXTURE)
    main_calls = [c for c in r.all_api_calls
                  if c.func_name and "main" in c.func_name]
    assert main_calls, "hello.main() not collected"
    for c in main_calls:
        assert c.top_library == "local", \
            f"hello.main top must be local, got {c.top_library}"
        assert "click" in c.decorated_by, \
            f"hello.main decorated_by must contain click, got {c.decorated_by}"


def test_hello_direct_decorated_by():
    """hello() top=local, decorated_by contains click."""
    r = analyze_project(_FIXTURE)
    hello_calls = [c for c in r.all_api_calls
                   if c.func_name == "hello"]
    assert hello_calls, "hello() not collected"
    for c in hello_calls:
        assert c.top_library == "local", \
            f"hello() top must be local, got {c.top_library}"
        assert "click" in c.decorated_by, \
            f"hello() decorated_by must contain click, got {c.decorated_by}"


def test_click_api_not_spuriously_decorated():
    """click.echo/command/option should NOT have decorated_by."""
    r = analyze_project(_FIXTURE)
    for c in r.all_api_calls:
        if c.func_name and c.func_name.startswith("click."):
            assert "click" not in c.decorated_by, \
                f"{c.func_name} must not have click in decorated_by"
