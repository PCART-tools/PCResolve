"""Regression tests for NumPy ndarray receiver ownership.

When scipy.linalg.svd() returns numpy ndarrays, method calls on
those arrays (e.g. .dot()) must be classified as numpy, not scipy.
Argument provenance must not override the callable receiver identity.
"""

from pcresolve import analyze_project
import os


FIXTURE_DIR = os.path.join(os.path.dirname(__file__),
                           "fixtures", "tested_projects", "machine-learning")


def _find_call(calls, expression_contains):
    for c in calls:
        if expression_contains in c.expression:
            return c
    return None


def test_uarr_dot_sarr_is_numpy():
    """uarr.dot(sarr) → numpy (receiver is numpy ndarray from svd)."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "uarr.dot(sarr)")
    assert call is not None, "uarr.dot(sarr) not found"
    assert call.top_library == "numpy", (
        "uarr.dot(sarr) should be numpy, got %s" % call.top_library)


def test_uarr_dot_sarr_dot_vharr_is_numpy():
    """uarr.dot(sarr).dot(vharr) → numpy (chained)."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "uarr.dot(sarr).dot(vharr)")
    assert call is not None, "uarr.dot(sarr).dot(vharr) not found"
    assert call.top_library == "numpy", (
        "uarr.dot(sarr).dot(vharr) should be numpy, got %s" % call.top_library)


def test_linalg_svd_is_scipy():
    """linalg.svd(arr) → scipy (the function itself is scipy)."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "linalg.svd(arr)")
    assert call is not None, "linalg.svd(arr) not found"
    assert call.top_library == "scipy", (
        "linalg.svd(arr) should be scipy, got %s" % call.top_library)


def test_stats_norm_pdf_is_scipy():
    """stats.norm.pdf(bins) → scipy."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "stats.norm.pdf")
    assert call is not None, "stats.norm.pdf(bins) not found"
    assert call.top_library == "scipy", (
        "stats.norm.pdf() should be scipy, got %s" % call.top_library)


def test_stats_norm_fit_is_scipy():
    """stats.norm.fit(a) → scipy."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "stats.norm.fit")
    assert call is not None, "stats.norm.fit(a) not found"
    assert call.top_library == "scipy", (
        "stats.norm.fit() should be scipy, got %s" % call.top_library)


def test_uarr_dot_not_in_scipy():
    """uarr.dot(sarr) must NOT appear under scipy."""
    result = analyze_project(FIXTURE_DIR)
    scipy_calls = [c for c in result.all_api_calls
                   if c.top_library == "scipy"]
    dot_in_scipy = [c for c in scipy_calls if "uarr.dot" in c.expression]
    assert len(dot_in_scipy) == 0, (
        "uarr.dot() should NOT be classified as scipy")


def test_np_diag_still_numpy():
    """np.diag(spec) → numpy (unchanged)."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "np.diag")
    assert call is not None, "np.diag() not found"
    assert call.top_library == "numpy", (
        "np.diag() should be numpy, got %s" % call.top_library)
