## @package tests.test_static_boundary_reviews
#  Regression tests for independently reviewed static source boundaries.

import json
import os
import sys


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from static_boundary_reviews import (  # noqa: E402
    project_source_digest,
    validate_static_boundary_reviews,
)


def _record(**overrides):
    record = {
        "project": "demo",
        "file": "main.py",
        "lineno": 2,
        "col_offset": 0,
        "expression": "value.method()",
        "expected_kind": "library",
        "expected_top_library": "external",
        "pcresolve_kind": "unknown",
        "pcresolve_top_library": "unknown",
        "status": "positive",
        "annotation_status": "locked",
    }
    record.update(overrides)
    return record


def _reviews(project_root, record=None):
    record = record or _record()
    return {
        "schema_version": 1,
        "reviews": [{
            "id": "demo-external-result",
            "project": "demo",
            "project_source_sha256": project_source_digest(str(project_root)),
            "reviewed_by": "source-audit",
            "reviewed_at": "2026-08-30",
            "reason": "receiver value is supplied only by an external API",
            "records": [{
                "file": record["file"],
                "lineno": record["lineno"],
                "col_offset": record["col_offset"],
                "expression": record["expression"],
                "expected_kind": record["expected_kind"],
                "expected_top_library": record["expected_top_library"],
            }],
        }],
    }


def _validate(tmp_path, reviews=None, records=None):
    return validate_static_boundary_reviews(
        reviews or _reviews(tmp_path),
        records or [_record()],
        {"demo": str(tmp_path)},
    )


def test_valid_review_maps_exact_unknown_mismatch(tmp_path):
    (tmp_path / "main.py").write_text(
        "value = external.make()\nvalue.method()\n", encoding="utf-8")

    accepted, errors = _validate(tmp_path)

    assert not errors
    assert len(accepted) == 1
    assert next(iter(accepted.values()))["id"] == "demo-external-result"


def test_project_digest_normalizes_line_endings(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "main.py").write_bytes(b"x = 1\r\ny = 2\r\n")
    (right / "main.py").write_bytes(b"x = 1\ny = 2\n")

    assert project_source_digest(str(left)) == project_source_digest(str(right))


def test_source_change_or_new_python_file_invalidates_review(tmp_path):
    source = tmp_path / "main.py"
    source.write_text(
        "value = external.make()\nvalue.method()\n", encoding="utf-8")
    reviews = _reviews(tmp_path)
    source.write_text(
        "value = local.make()\nvalue.method()\n", encoding="utf-8")

    _, errors = _validate(tmp_path, reviews=reviews)
    assert any("source digest" in error for error in errors)

    source.write_text(
        "value = external.make()\nvalue.method()\n", encoding="utf-8")
    reviews = _reviews(tmp_path)
    (tmp_path / "extra.py").write_text("value = 1\n", encoding="utf-8")
    _, errors = _validate(tmp_path, reviews=reviews)
    assert any("source digest" in error for error in errors)


def test_changed_gt_owner_invalidates_review(tmp_path):
    (tmp_path / "main.py").write_text(
        "value = external.make()\nvalue.method()\n", encoding="utf-8")
    reviews = _reviews(tmp_path)
    changed = _record(
        expected_kind="python", expected_top_library="python")

    _, errors = _validate(tmp_path, reviews=reviews, records=[changed])

    assert any("expected owner" in error for error in errors)


def test_expression_must_identify_exact_call_ast(tmp_path):
    (tmp_path / "main.py").write_text(
        "value = external.make()\nvalue.other()\n", encoding="utf-8")
    reviews = _reviews(tmp_path)
    reviews["reviews"][0]["project_source_sha256"] = (
        project_source_digest(str(tmp_path)))

    _, errors = _validate(tmp_path, reviews=reviews)

    assert any("source call" in error for error in errors)


def test_duplicate_record_and_non_unknown_mismatch_are_rejected(tmp_path):
    (tmp_path / "main.py").write_text(
        "value = external.make()\nvalue.method()\n", encoding="utf-8")
    reviews = _reviews(tmp_path)
    duplicate = json.loads(json.dumps(reviews["reviews"][0]))
    duplicate["id"] = "duplicate"
    reviews["reviews"].append(duplicate)

    _, errors = _validate(tmp_path, reviews=reviews)
    assert any("duplicate reviewed record" in error for error in errors)

    reviews["reviews"].pop()
    wrong_certainty = _record(
        pcresolve_kind="local", pcresolve_top_library="local")
    _, errors = _validate(
        tmp_path, reviews=reviews, records=[wrong_certainty])
    assert any("unknown/unknown" in error for error in errors)


def test_review_may_remain_after_analyzer_becomes_correct(tmp_path):
    (tmp_path / "main.py").write_text(
        "value = external.make()\nvalue.method()\n", encoding="utf-8")
    reviews = _reviews(tmp_path)
    matched = _record(
        pcresolve_kind="library", pcresolve_top_library="external")

    accepted, errors = _validate(
        tmp_path, reviews=reviews, records=[matched])

    assert not errors
    assert not accepted


def test_review_level_expected_owner_may_cover_homogeneous_group(tmp_path):
    (tmp_path / "main.py").write_text(
        "value = external.make()\nvalue.method()\n", encoding="utf-8")
    reviews = _reviews(tmp_path)
    group = reviews["reviews"][0]
    group["expected_kind"] = group["records"][0].pop("expected_kind")
    group["expected_top_library"] = group["records"][0].pop(
        "expected_top_library")

    accepted, errors = _validate(tmp_path, reviews=reviews)

    assert not errors
    assert len(accepted) == 1
