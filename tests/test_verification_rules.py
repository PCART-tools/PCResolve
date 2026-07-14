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
from evaluate_ground_truth import pos_key, match_position, _normalize_expr


def test_return_propagation_downgraded_to_static_context():
    """_classify may return static_obvious but add_levels must downgrade."""
    # Build a record that would be classified as static_obvious by _classify
    rec = {
        "source": "pcresolve_candidate",
        "project": "test",
        "file": "test.py",
        "lineno": 1,
        "col_offset": 0,
        "expression": "conn.commit()",
        "pcresolve_kind": "library",
        "pcresolve_top_library": "mysql",
        "pcresolve_reason": "RETURN_PROPAGATION",
        "pcresolve_alternatives": ["mysql"],
        "pcresolve_decorated_by": [],
        "expected_kind": "library",
        "expected_top_library": "mysql",
        "expected_alternatives": [],
        "expected_decorated_by": [],
        "status": "positive",
        "annotation_status": "locked",
        "category": "transitive_method",
        "notes": "conn from mysql.connector.connect return",
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
        "expression": "conn.commit()",
        "pcresolve_kind": "library",
        "pcresolve_top_library": "mysql",
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
                assert "pyprind" in r.get("verification_notes", "").lower(), (
                    "verification_notes should mention pyprind, "
                    "got: %s" % r.get("verification_notes", ""))
                return


# ── CLI aliases ──────────────────────────────────────────────────────────


def test_include_unlocked_alias_matches_include_draft():
    """--include-unlocked produces exactly the same aggregate as --include-draft."""
    import subprocess
    def run_eval(flag):
        args = [sys.executable,
                os.path.join(os.path.dirname(__file__), "..",
                             "scripts", "evaluate_ground_truth.py"),
                flag, "--view", "all"]
        r = subprocess.run(args, capture_output=True, text=True)
        assert r.returncode == 0, "evaluator exited %d" % r.returncode
        for line in r.stdout.splitlines():
            if "Aggregate" in line:
                return line.strip()
        return None

    draft = run_eval("--include-draft")
    unlocked = run_eval("--include-unlocked")
    assert draft is not None, "--include-draft returned no Aggregate line"
    assert unlocked is not None, "--include-unlocked returned no Aggregate line"
    assert draft == unlocked, (
        "Alias mismatch:\n  --include-draft:     %s\n  --include-unlocked:  %s"
        % (draft, unlocked))


def test_help_includes_new_flag():
    """--help output mentions --include-unlocked."""
    import subprocess
    args = [sys.executable,
            os.path.join(os.path.dirname(__file__), "..",
                         "scripts", "evaluate_ground_truth.py"),
            "--help"]
    r = subprocess.run(args, capture_output=True, text=True)
    assert r.returncode == 0, "evaluator --help exited %d" % r.returncode
    assert "--include-unlocked" in r.stdout, (
        "--help should mention --include-unlocked")


# ── Position-first matching ──────────────────────────────────────────────


def test_pos_key_no_expression():
    """pos_key uses only (file, lineno, col_offset), not expression."""
    rec = {"project": "test", "file": "f.py", "lineno": 1, "col_offset": 0,
           "expression": "dontcare"}
    key = pos_key(rec)
    assert len(key) == 4, key
    assert key[3] == 0  # col_offset
    assert "dontcare" not in key


def test_match_position_single_candidate():
    """Single GT + single PC → direct match."""
    matches, remaining = match_position(
        [(0, {"expression": "x.y()"})],
        [{"top_library": "numpy", "expression": "x.y()"}])
    assert len(matches) == 1
    assert matches[0]["top_library"] == "numpy"
    assert len(remaining) == 0


def test_two_gt_one_pc_no_reuse():
    """2 GT + 1 PC at same position → 1 hit + 1 miss, no reuse."""
    gt_entries = [
        (0, {"expression": "a().b()"}),
        (1, {"expression": "a()"}),
    ]
    pc = [{"top_library": "numpy", "expression": "a().b()"}]
    matches, remaining = match_position(gt_entries, pc)
    # Only one PC candidate → at most one GT can match
    assert len(matches) == 1
    assert len(remaining) == 0
    # The matched GT should be the one whose expression matches
    assert 0 in matches  # a().b() matches
    assert 1 not in matches  # a() has no candidate


def test_one_gt_two_pc_produces_uncovered():
    """1 GT + 2 PC at same position → 1 hit + 1 remaining (uncovered)."""
    gt_entries = [(0, {"expression": "a().b()"})]
    pc = [
        {"top_library": "numpy", "expression": "a().b()"},
        {"top_library": "python", "expression": "a()"},
    ]
    matches, remaining = match_position(gt_entries, pc)
    assert len(matches) == 1
    assert matches[0]["top_library"] == "numpy"
    assert len(remaining) == 1
    assert remaining[0]["top_library"] == "python"


def test_match_position_expression_fallback():
    """Multiple candidates → match by normalized expression."""
    gt_entries = [(0, {"expression": "x.reshape((3,3))"}),
                  (1, {"expression": "print('ok')"})]
    pc = [{"top_library": "numpy", "expression": "x.reshape((3,3))"},
          {"top_library": "python", "expression": "print('ok')"}]
    matches, remaining = match_position(gt_entries, pc)
    assert len(matches) == 2
    assert matches[0]["top_library"] == "numpy"
    assert matches[1]["top_library"] == "python"
    assert len(remaining) == 0


def test_comprehension_parens_equivalent():
    """`for (k, v)` and `for k, v` normalize to the same string."""
    e1 = "print({k: v for (k, v) in sorted(x)})"
    e2 = "print({k: v for k, v in sorted(x)})"
    assert _normalize_expr(e1) == _normalize_expr(e2)


# ── Schema type validation ────────────────────────────────────────────────


def test_expected_alternatives_string_fails_lock_check():
    """--check must fail when expected_alternatives is a string, not a list."""
    rec = {
        "file": "test.py", "lineno": 1, "col_offset": 0,
        "expression": "foo.bar()", "project": "test",
        "expected_kind": "library", "expected_top_library": "numpy",
        "expected_alternatives": "",
        "status": "positive",
        "annotation_status": "reviewed",
        "category": "transitive_method",
        "verification_level": "static_context",
        "verification_notes": "test record",
    }

    with tempfile.TemporaryDirectory() as tmp:
        jsonl_path = os.path.join(tmp, "test.jsonl")
        with open(jsonl_path, "w") as f:
            f.write(json.dumps(rec) + "\n")

        import add_verification_levels as avl
        old_calls = avl.CALLS_DIR
        old_proj = avl.PROJECTS_FILE
        avl.CALLS_DIR = tmp
        proj_manifest = os.path.join(tmp, "projects.json")
        with open(proj_manifest, "w") as f:
            json.dump({"projects": {"test": {"status": "reviewed"}}}, f)
        avl.PROJECTS_FILE = proj_manifest

        try:
            result = check_lock("test")
        finally:
            avl.CALLS_DIR = old_calls
            avl.PROJECTS_FILE = old_proj

    assert result is not None, "check_lock returned None"
    assert result["ok"] is False, (
        "check_lock must fail when expected_alternatives is a string")
    blocker_msgs = " ".join(result["blockers"])
    assert "expected_alternatives must be a list" in blocker_msgs, (
        "blockers must mention expected_alternatives type, got: %s" % blocker_msgs)


def test_expected_alternatives_list_passes_lock_check():
    """--check must pass when expected_alternatives is a proper list."""
    rec = {
        "file": "test.py", "lineno": 1, "col_offset": 0,
        "expression": "foo.bar()", "project": "test",
        "expected_kind": "library", "expected_top_library": "numpy",
        "expected_alternatives": [],
        "status": "positive",
        "annotation_status": "reviewed",
        "category": "transitive_method",
        "verification_level": "static_context",
        "verification_notes": "test record",
    }

    with tempfile.TemporaryDirectory() as tmp:
        jsonl_path = os.path.join(tmp, "test.jsonl")
        with open(jsonl_path, "w") as f:
            f.write(json.dumps(rec) + "\n")

        import add_verification_levels as avl
        old_calls = avl.CALLS_DIR
        old_proj = avl.PROJECTS_FILE
        avl.CALLS_DIR = tmp
        proj_manifest = os.path.join(tmp, "projects.json")
        with open(proj_manifest, "w") as f:
            json.dump({"projects": {"test": {"status": "reviewed"}}}, f)
        avl.PROJECTS_FILE = proj_manifest

        try:
            result = check_lock("test")
        finally:
            avl.CALLS_DIR = old_calls
            avl.PROJECTS_FILE = old_proj

    assert result is not None, "check_lock returned None"
    assert result["ok"] is True, (
        "check_lock must pass for valid list expected_alternatives, "
        "blockers: %s" % result.get("blockers", []))


# ── Project field invariant ─────────────────────────────────────────────


def _make_reviewed_record(project_name="test"):
    return {
        "file": "test.py", "lineno": 1, "col_offset": 0,
        "expression": "foo.bar()", "project": project_name,
        "expected_kind": "library", "expected_top_library": "numpy",
        "expected_alternatives": [],
        "status": "positive",
        "annotation_status": "reviewed",
        "category": "transitive_method",
        "verification_level": "static_context",
        "verification_notes": "test record",
    }


def _run_check_with_records(proj_name, records, manifest_status="reviewed"):
    with tempfile.TemporaryDirectory() as tmp:
        jsonl_path = os.path.join(tmp, f"{proj_name}.jsonl")
        with open(jsonl_path, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")

        import add_verification_levels as avl
        old_calls, old_proj = avl.CALLS_DIR, avl.PROJECTS_FILE
        avl.CALLS_DIR = tmp
        proj_manifest = os.path.join(tmp, "projects.json")
        with open(proj_manifest, "w") as f:
            json.dump({"projects": {proj_name: {"status": manifest_status}}}, f)
        avl.PROJECTS_FILE = proj_manifest

        try:
            return check_lock(proj_name)
        finally:
            avl.CALLS_DIR = old_calls
            avl.PROJECTS_FILE = old_proj


def test_project_field_matches_jsonl_name_passes():
    """project field matches JSONL name -> pass."""
    rec = _make_reviewed_record(project_name="simulation")
    result = _run_check_with_records("simulation", [rec])
    assert result is not None
    assert result["ok"] is True, (
        "check_lock must pass when project matches JSONL name, "
        "blockers: %s" % result.get("blockers", []))


def test_project_field_mismatch_fails():
    """project field differs from JSONL name -> fail."""
    rec = _make_reviewed_record(project_name="ex_4_2")
    result = _run_check_with_records("simulation", [rec])
    assert result is not None
    assert result["ok"] is False, (
        "check_lock must fail when project field mismatches JSONL name")
    blocker_msgs = " ".join(result["blockers"])
    assert "project field mismatch" in blocker_msgs, (
        "blockers must mention project field mismatch, got: %s" % blocker_msgs)


# ── Evaluation completeness ─────────────────────────────────────────────


def test_evaluator_reports_awaiting_annotation():
    """evaluate_one counts records awaiting annotation (draft, no expected_kind)."""
    import tempfile, os, json
    with tempfile.TemporaryDirectory() as tmp:
        # Partially-annotated project: one auto_labeled, one draft
        recs = [
            {"project": "testproj", "file": "a.py", "lineno": 1, "col_offset": 0,
             "expression": "np.array()",
             "expected_kind": "library", "expected_top_library": "numpy",
             "expected_alternatives": [],
             "status": "positive", "annotation_status": "auto_labeled",
             "verification_level": "static_obvious",
             "verification_notes": "direct import"},
            {"project": "testproj", "file": "a.py", "lineno": 2, "col_offset": 0,
             "expression": "foo.bar()",
             "annotation_status": "draft"},
        ]
        jsonl = os.path.join(tmp, "testproj.jsonl")
        with open(jsonl, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")

        proj = os.path.join(tmp, "projects.json")
        with open(proj, "w") as f:
            json.dump({"projects": {
                "testproj": {"path": tmp, "status": "draft"}
            }}, f)

        import evaluate_ground_truth as ev
        old_gt = ev.GT_DIR
        old_calls = ev.CALLS_DIR
        old_proj = ev.PROJECTS_FILE
        ev.GT_DIR = tmp
        ev.CALLS_DIR = tmp
        ev.PROJECTS_FILE = proj
        try:
            m = ev.evaluate_one("testproj",
                                {"path": tmp, "status": "draft"}, view="all")
        finally:
            ev.GT_DIR = old_gt
            ev.CALLS_DIR = old_calls
            ev.PROJECTS_FILE = old_proj

    assert m is not None
    assert m["records_total"] == 2, f"records_total: {m['records_total']}"
    assert m["records_scored"] == 0, f"records_scored: {m['records_scored']} (default excludes auto_labeled)"
    assert m["awaiting_annotation"] == 1, f"awaiting: {m['awaiting_annotation']}"
    assert m["gt_positive"] == 0  # auto_labeled excluded by default
    assert m["auto_labeled"] == 1


def test_evaluator_include_auto_labeled_scores_auto():
    """--include-auto-labeled includes auto_labeled records in scoring."""
    import tempfile, os, json
    with tempfile.TemporaryDirectory() as tmp:
        recs = [
            {"project": "testproj", "file": "a.py", "lineno": 1, "col_offset": 0,
             "expression": "np.array()",
             "expected_kind": "library", "expected_top_library": "numpy",
             "expected_alternatives": [],
             "status": "positive", "annotation_status": "auto_labeled",
             "verification_level": "static_obvious",
             "verification_notes": "direct import"},
        ]
        jsonl = os.path.join(tmp, "testproj.jsonl")
        with open(jsonl, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        proj = os.path.join(tmp, "projects.json")
        with open(proj, "w") as f:
            json.dump({"projects": {"testproj": {"path": tmp, "status": "locked"}}}, f)

        import evaluate_ground_truth as ev
        old_gt, old_calls, old_proj = ev.GT_DIR, ev.CALLS_DIR, ev.PROJECTS_FILE
        ev.GT_DIR = tmp; ev.CALLS_DIR = tmp; ev.PROJECTS_FILE = proj
        try:
            m = ev.evaluate_one("testproj", {"path": tmp, "status": "locked"},
                                view="all", include_auto_labeled=True)
        finally:
            ev.GT_DIR = old_gt; ev.CALLS_DIR = old_calls; ev.PROJECTS_FILE = old_proj

    assert m is not None
    assert m["records_scored"] == 1, f"include_auto scores auto_labeled: {m['records_scored']}"
    assert m["gt_positive"] == 1
    assert m["auto_labeled"] == 1


# ── auto_label_gt idempotency ─────────────────────────────────────────────


def test_auto_label_chained_call_stays_draft_on_rerun():
    """Chained calls with static_context must stay draft on re-run."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
    from auto_label_gt import _auto_label

    rec = {
        "pcresolve_reason": "TRANSITIVE_IMPORT",
        "pcresolve_func_name": "scipy.stats.norm().ppf",
        "pcresolve_top_library": "scipy",
    }
    # First run
    ok = _auto_label(rec)
    assert ok is True
    assert rec["verification_level"] == "static_context"
    assert rec["annotation_status"] == "draft", f"first run: {rec['annotation_status']}"
    # Second run (idempotent)
    ok2 = _auto_label(rec)
    assert ok2 is True
    assert rec["annotation_status"] == "draft", f"second run overwrote: {rec['annotation_status']}"


# ── Evaluator metric mutual exclusivity ───────────────────────────────────


def test_awaiting_counts_are_mutually_exclusive():
    """awaiting_annotation, awaiting_review, auto_labeled must not overlap."""
    import tempfile, os, json
    with tempfile.TemporaryDirectory() as tmp:
        recs = [
            {"project": "tp", "file": "a.py", "lineno": 1, "col_offset": 0,
             "expression": "draft_no_label()",
             "annotation_status": "draft"},  # awaiting_annotation
            {"project": "tp", "file": "a.py", "lineno": 2, "col_offset": 0,
             "expression": "draft_labeled()",
             "expected_kind": "library", "expected_top_library": "x",
             "expected_alternatives": [],
             "status": "positive", "annotation_status": "draft"},  # awaiting_review
            {"project": "tp", "file": "a.py", "lineno": 3, "col_offset": 0,
             "expression": "auto()",
             "expected_kind": "library", "expected_top_library": "y",
             "expected_alternatives": [],
             "status": "positive", "annotation_status": "auto_labeled",
             "verification_level": "static_obvious",
             "verification_notes": "ok"},  # auto_labeled
        ]
        jsonl = os.path.join(tmp, "tp.jsonl")
        with open(jsonl, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        proj = os.path.join(tmp, "projects.json")
        with open(proj, "w") as f:
            json.dump({"projects": {"tp": {"path": tmp, "status": "draft"}}}, f)

        import evaluate_ground_truth as ev
        old_gt, old_calls, old_proj = ev.GT_DIR, ev.CALLS_DIR, ev.PROJECTS_FILE
        ev.GT_DIR = tmp; ev.CALLS_DIR = tmp; ev.PROJECTS_FILE = proj
        try:
            m = ev.evaluate_one("tp", {"path": tmp, "status": "draft"}, view="all")
        finally:
            ev.GT_DIR = old_gt; ev.CALLS_DIR = old_calls; ev.PROJECTS_FILE = old_proj

    assert m is not None
    assert m["awaiting_annotation"] == 1, f"awaiting_annotation: {m['awaiting_annotation']}"
    assert m["awaiting_review"] == 1, f"awaiting_review: {m['awaiting_review']}"
    assert m["auto_labeled"] == 1, f"auto_labeled: {m['auto_labeled']}"
    assert m["awaiting_annotation"] + m["awaiting_review"] + m["auto_labeled"] == 3


def test_draft_negative_excluded_from_default_scoring():
    """Draft negative/unsupported records not scored by default."""
    import tempfile, os, json
    with tempfile.TemporaryDirectory() as tmp:
        recs = [
            {"project": "tp", "file": "a.py", "lineno": 1, "col_offset": 0,
             "expression": "bad()", "status": "negative",
             "expected_kind": "library", "expected_top_library": "x",
             "expected_alternatives": [],
             "annotation_status": "draft"},  # draft negative -> excluded
        ]
        jsonl = os.path.join(tmp, "tp.jsonl")
        with open(jsonl, "w") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        proj = os.path.join(tmp, "projects.json")
        with open(proj, "w") as f:
            json.dump({"projects": {"tp": {"path": tmp, "status": "draft"}}}, f)

        import evaluate_ground_truth as ev
        old_gt, old_calls, old_proj = ev.GT_DIR, ev.CALLS_DIR, ev.PROJECTS_FILE
        ev.GT_DIR = tmp; ev.CALLS_DIR = tmp; ev.PROJECTS_FILE = proj
        try:
            m = ev.evaluate_one("tp", {"path": tmp, "status": "draft"}, view="all")
        finally:
            ev.GT_DIR = old_gt; ev.CALLS_DIR = old_calls; ev.PROJECTS_FILE = old_proj

    assert m is not None
    assert m["gt_negative"] == 0, f"draft negative excluded: {m['gt_negative']}"
    assert m["records_scored"] == 0


def test_help_includes_include_auto_labeled():
    """--help output mentions --include-auto-labeled."""
    import subprocess, sys, os
    r = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "..",
         "scripts", "evaluate_ground_truth.py"), "--help"],
        capture_output=True, text=True)
    assert r.returncode == 0
    assert "--include-auto-labeled" in r.stdout, (
        "--help must mention --include-auto-labeled")
