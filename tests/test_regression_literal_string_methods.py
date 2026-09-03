"""Regression tests for literal string/bytes method classification.

Literal string/bytes method calls (e.g. "{}".format()) must be
classified as python since the receiver is a builtin type.

Also tests the _is_suspicious manual_gt matching logic for the
ground truth review renderer.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from render_ground_truth_review import _is_suspicious
from pcresolve import analyze_project


FIXTURE_DIR = os.path.join(os.path.dirname(__file__),
                           "fixtures", "literal_string_methods")


def _find_call(calls, expression_contains):
    for c in calls:
        if expression_contains in c.expression:
            return c
    return None


def test_literal_str_format_is_python():
    """'{}'  .format(42) → python."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "'{}'.format")
    assert call is not None, "\"'{}'.format(...)\" not found in output"
    assert call.top_library == "python", (
        "\"'{}'.format()\" should be python, got %s" % call.top_library)


def test_literal_bytes_split_is_python():
    """b'hello world'.split() → python."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "b'hello world'.split")
    assert call is not None, "b'hello world'.split() not found in output"
    assert call.top_library == "python", (
        "b'hello world'.split() should be python, got %s" % call.top_library)


def test_literal_str_format_has_correct_reason():
    """Literal str.format() should have BUILTIN reason and confidence=1.0."""
    result = analyze_project(FIXTURE_DIR)
    call = _find_call(result.all_api_calls, "'{}'.format")
    assert call is not None
    assert call.reason == "BUILTIN", (
        "reason should be BUILTIN, got %s" % call.reason)
    assert call.confidence == 1.0, (
        "confidence should be 1.0, got %s" % call.confidence)


# ── _is_suspicious manual_gt matching logic ──────────────────────────────


def _make_record(source="pcresolve_candidate", ek="python", etl="python",
                 pck="python", pctl="python", palts=None, **kw):
    """Build a minimal GT record dict for _is_suspicious testing."""
    r = {
        "source": source, "expected_kind": ek, "expected_top_library": etl,
        "pcresolve_kind": pck, "pcresolve_top_library": pctl,
        "pcresolve_alternatives": palts if palts is not None else [],
        "pcresolve_decorated_by": [], "expected_decorated_by": [],
        "verification_level": "static_obvious", "status": "positive",
    }
    r.update(kw)
    return r


def test_manual_gt_full_match_empty_alternatives_not_suspicious():
    """manual GT + full kind/owner match + empty alternatives → not suspicious."""
    r = _make_record(source="manual_gt", pck="python", pctl="python",
                     ek="python", etl="python", palts=[])
    assert not _is_suspicious(r), (
        "manual_gt with full match should not be suspicious")


def test_manual_gt_owner_mismatch_is_suspicious():
    """manual GT + owner mismatch → suspicious."""
    r = _make_record(source="manual_gt", pck="python", pctl="python",
                     ek="python", etl="local", palts=[])
    assert _is_suspicious(r), (
        "manual_gt with owner mismatch should be suspicious")


def test_manual_gt_expected_owner_in_alternatives_not_suspicious():
    """manual GT + expected owner in alternatives → not suspicious."""
    r = _make_record(source="manual_gt", pck="library", pctl="numpy",
                     ek="library", etl="scipy", palts=["scipy", "numpy"])
    assert not _is_suspicious(r), (
        "manual_gt with expected owner in alternatives should not be suspicious")


def test_manual_gt_empty_pcresolve_is_suspicious():
    """manual GT + empty pcresolve fields → suspicious."""
    r = _make_record(source="manual_gt", pck="", pctl="",
                     ek="python", etl="python", palts=[])
    assert _is_suspicious(r), (
        "manual_gt with empty pcresolve fields should be suspicious")


def test_manual_gt_kind_mismatch_is_suspicious():
    """manual GT + kind mismatch → suspicious."""
    r = _make_record(source="manual_gt", pck="local", pctl="local",
                     ek="python", etl="python", palts=[])
    assert _is_suspicious(r), (
        "manual_gt with kind mismatch should be suspicious")
