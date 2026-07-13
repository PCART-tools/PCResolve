"""Regression tests: method calls on ast.Compare expression receivers.

(a == b).any() where both sides are numpy → classified as numpy.
"""

from pcresolve import analyze_project
import os


FIXTURE_DIR = os.path.join(os.path.dirname(__file__),
                           "fixtures", "compare_receiver")


def _find_call(calls, expression_contains):
    for c in calls:
        if expression_contains in c.expression:
            return c
    return None


def test_compare_any_collected():
    """(np.diag(W) == np.zeros(...)).any() is collected."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, ").any()")
    assert call is not None, (
        "(np.diag(W)==np.zeros(...)).any() not collected")


def test_compare_any_is_numpy():
    """(np.diag(W) == np.zeros(...)).any() → numpy."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, ").any()")
    assert call is not None
    assert call.top_library == "numpy", (
        ".any() on numpy compare result should be numpy, got %s"
        % call.top_library)


def test_compare_all_is_numpy():
    """(np.diag(W) == np.zeros(...)).all() → numpy."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, ").all()")
    assert call is not None
    assert call.top_library == "numpy", (
        ".all() on numpy compare result should be numpy, got %s"
        % call.top_library)


def test_np_diag_still_collected():
    """np.diag(W) is still collected as numpy."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "np.diag")
    assert call is not None, "np.diag(W) not collected"
    assert call.top_library == "numpy"


def test_np_zeros_still_collected():
    """np.zeros(...) is still collected as numpy."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "np.zeros")
    assert call is not None, "np.zeros(...) not collected"
    assert call.top_library == "numpy"


def test_local_compare_not_numpy():
    """Local int comparison .any() → unknown (collected, not numpy)."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "a == b).any()")
    assert call is not None, (
        "local (a == b).any() must still be collected, got None")
    assert call.top_library == "unknown", (
        "local (a == b).any() should be unknown, got %s"
        % call.top_library)


def test_compare_any_not_duplicated():
    """Each .any() call on compare should appear exactly once per site."""
    result = analyze_project(FIXTURE_DIR)
    # Should have exactly 2 any() calls: one numpy, one local
    any_calls = [c for c in result.all_api_calls if ").any()" in c.expression]
    assert len(any_calls) == 2, (
        "Expected 2 .any() calls (numpy compare + local compare), got %d: %s"
        % (len(any_calls), [c.expression for c in any_calls]))
    # Must include the numpy compare .any()
    numpy_any = [c for c in any_calls if c.top_library == "numpy"]
    assert len(numpy_any) == 1, (
        "Expected exactly 1 numpy compare .any(), got %d" % len(numpy_any))


def test_compare_all_not_duplicated():
    """The .all() call should appear exactly once."""
    result = analyze_project(FIXTURE_DIR)
    all_calls = [c for c in result.all_api_calls if ").all()" in c.expression]
    assert len(all_calls) == 1, (
        "Expected exactly 1 .all() call, got %d: %s"
        % (len(all_calls), [c.expression for c in all_calls]))


