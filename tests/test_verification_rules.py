"""Regression tests for verification_level constraint rules.

RETURN_PROPAGATION records must never be classified as static_obvious
because their receiver identity depends on return-value propagation.
"""

import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from add_verification_levels import add_levels, check_lock


def test_return_propagation_downgraded_to_static_context():
    """_classify may return static_obvious but add_levels must downgrade."""
    # Build a record that would be classified as static_obvious by _classify
    rec = {
        "source": "pcresolve_candidate",
        "project": "test",
        "file": "test.py",
        "lineno": 1,
        "col_offset": 0,
        "expression": "my_prbar.update()",
        "pcresolve_kind": "library",
        "pcresolve_top_library": "pyprind",
        "pcresolve_reason": "RETURN_PROPAGATION",
        "pcresolve_alternatives": ["pyprind"],
        "pcresolve_decorated_by": [],
        "expected_kind": "library",
        "expected_top_library": "pyprind",
        "expected_alternatives": [],
        "expected_decorated_by": [],
        "status": "positive",
        "annotation_status": "locked",
        "category": "transitive_method",
        "notes": "ProgBar update method",
        "verification_level": "static_obvious",
        "verification_notes": "old wrong note",
    }

    # Write to temp JSONL, run add_levels (not dry_run, to write back)
    with tempfile.TemporaryDirectory() as tmp:
        jsonl_path = os.path.join(tmp, "test.jsonl")
        with open(jsonl_path, "w") as f:
            f.write(json.dumps(rec) + "\n")

        import add_verification_levels as avl
        old_calls = avl.CALLS_DIR
        avl.CALLS_DIR = tmp
        try:
            add_levels("test", dry_run=False)
        finally:
            avl.CALLS_DIR = old_calls

        # Read back the classified record from disk
        with open(jsonl_path) as f:
            rec_out = json.loads(f.readline())

    assert rec_out["verification_level"] == "static_context", (
        "RETURN_PROPAGATION must be downgraded to static_context, "
        "got %s" % rec_out["verification_level"])
    assert "return-value propagation" in rec_out.get("verification_notes", ""), (
        "verification_notes should mention return-value propagation")


def test_check_lock_blocks_return_propagation_static_obvious():
    """check_lock must fail when RETURN_PROPAGATION + static_obvious."""
    rec = {
        "source": "pcresolve_candidate",
        "project": "test",
        "file": "test.py",
        "lineno": 1,
        "col_offset": 0,
        "expression": "my_prbar.update()",
        "pcresolve_kind": "library",
        "pcresolve_top_library": "pyprind",
        "pcresolve_reason": "RETURN_PROPAGATION",
        "status": "positive",
        "annotation_status": "locked",
        "category": "transitive_method",
        "verification_level": "static_obvious",
        "verification_notes": "wrong note",
    }

    with tempfile.TemporaryDirectory() as tmp:
        jsonl_path = os.path.join(tmp, "test.jsonl")
        with open(jsonl_path, "w") as f:
            f.write(json.dumps(rec) + "\n")

        # Patch projects manifest
        import add_verification_levels as avl
        old_calls = avl.CALLS_DIR
        old_proj = avl.PROJECTS_FILE
        avl.CALLS_DIR = tmp
        proj_manifest = os.path.join(tmp, "projects.json")
        with open(proj_manifest, "w") as f:
            json.dump({"projects": {"test": {"status": "locked"}}}, f)
        avl.PROJECTS_FILE = proj_manifest

        try:
            result = check_lock("test")
        finally:
            avl.CALLS_DIR = old_calls
            avl.PROJECTS_FILE = old_proj

    assert result is not None, "check_lock returned None"
    assert result["ok"] is False, (
        "check_lock must fail for RETURN_PROPAGATION + static_obvious")
    blocker_msgs = " ".join(result["blockers"])
    assert "RETURN_PROPAGATION" in blocker_msgs, (
        "blockers must mention RETURN_PROPAGATION, got: %s" % blocker_msgs)


def test_existing_youtube_record_is_static_context():
    """The my_prbar.update() record in Youtube.jsonl is now static_context."""
    gt_path = os.path.join(
        os.path.dirname(__file__), "..",
        "ground_truth", "calls", "Youtube.jsonl")
    with open(gt_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if "my_prbar.update" in r.get("expression", ""):
                assert r.get("verification_level") == "static_context", (
                    "my_prbar.update() must be static_context, "
                    "got %s" % r.get("verification_level"))
                assert "return" in r.get("verification_notes", "").lower(), (
                    "verification_notes should explain propagation")
                return
    assert False, "my_prbar.update() record not found in Youtube.jsonl"
