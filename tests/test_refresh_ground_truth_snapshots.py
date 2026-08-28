## @package tests.test_refresh_ground_truth_snapshots
#  Safety contract for refreshing PCResolve fields in reviewed GT records.

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import refresh_ground_truth_snapshots as refresh_module
from refresh_ground_truth_snapshots import refresh_records


def _record(expression="obj.run()", top="local"):
    return {
        "source": "manual_gt",
        "project": "demo",
        "file": "main.py",
        "lineno": 4,
        "col_offset": 0,
        "expression": expression,
        "pcresolve_kind": "local",
        "pcresolve_top_library": top,
        "pcresolve_alternatives": [],
        "pcresolve_decorated_by": [],
        "pcresolve_reason": "LOCAL_DEFINITION",
        "pcresolve_confidence": 1.0,
        "pcresolve_func_name": "obj.run",
        "expected_kind": "library",
        "expected_top_library": "requests",
        "status": "positive",
        "annotation_status": "locked",
        "verification_level": "dynamic_probe",
        "verification_notes": "human evidence",
        "notes": "keep this note",
    }


def _call(root, expression="obj.run()", top="requests", col=0):
    return SimpleNamespace(
        file_path=os.path.join(root, "main.py"),
        lineno=4,
        col_offset=col,
        expression=expression,
        top_library=top,
        alternatives=[top],
        decorated_by=[],
        reason="RETURN_PROPAGATION",
        confidence=0.85,
        func_name="obj.run",
    )


def test_refresh_updates_only_pcresolve_snapshot_fields(tmp_path):
    original = _record()
    refreshed, changed, uncovered = refresh_records(
        "demo", [original], [_call(str(tmp_path))], str(tmp_path))

    assert changed == 1
    assert uncovered == []
    assert refreshed[0]["pcresolve_kind"] == "library"
    assert refreshed[0]["pcresolve_top_library"] == "requests"
    assert refreshed[0]["pcresolve_reason"] == "RETURN_PROPAGATION"
    assert refreshed[0]["source"] == "manual_gt"
    assert refreshed[0]["expected_kind"] == "library"
    assert refreshed[0]["expected_top_library"] == "requests"
    assert refreshed[0]["annotation_status"] == "locked"
    assert refreshed[0]["verification_notes"] == "human evidence"
    assert refreshed[0]["notes"] == "keep this note"


def test_refresh_clears_stale_snapshot_when_candidate_is_missing(tmp_path):
    refreshed, changed, uncovered = refresh_records(
        "demo", [_record()], [], str(tmp_path))

    assert changed == 1
    assert uncovered == []
    assert refreshed[0]["pcresolve_kind"] == ""
    assert refreshed[0]["pcresolve_top_library"] == ""
    assert refreshed[0]["pcresolve_alternatives"] == []
    assert refreshed[0]["pcresolve_reason"] == ""
    assert refreshed[0]["pcresolve_confidence"] == 0.0


def test_refresh_matches_same_position_calls_once_by_expression(tmp_path):
    first = _record("obj.first()", "stale")
    second = _record("obj.second()", "stale")
    calls = [
        _call(str(tmp_path), "obj.second()", "json"),
        _call(str(tmp_path), "obj.first()", "requests"),
    ]

    refreshed, changed, uncovered = refresh_records(
        "demo", [first, second], calls, str(tmp_path))

    assert changed == 2
    assert uncovered == []
    assert refreshed[0]["pcresolve_top_library"] == "requests"
    assert refreshed[1]["pcresolve_top_library"] == "json"


def test_refresh_reports_uncovered_prediction(tmp_path):
    call = _call(str(tmp_path), "extra()", "json", col=2)
    refreshed, changed, uncovered = refresh_records(
        "demo", [_record()], [call], str(tmp_path))

    assert changed == 1
    assert len(uncovered) == 1
    assert uncovered[0]["expression"] == "extra()"


def test_cli_fails_when_updates_and_uncovered_predictions_coexist(
        tmp_path, monkeypatch):
    changed_root = tmp_path / "changed"
    uncovered_root = tmp_path / "uncovered"
    changed_root.mkdir()
    uncovered_root.mkdir()
    calls_dir = tmp_path / "calls"
    calls_dir.mkdir()

    manifest = {
        "changed": {"path": str(changed_root), "status": "locked"},
        "uncovered": {"path": str(uncovered_root), "status": "locked"},
    }

    def records(name):
        record = _record()
        record["project"] = name
        return [record]

    def analyze(root):
        calls = [_call(root)]
        if root == str(uncovered_root):
            calls.append(_call(root, "extra()", "json", col=2))
        return SimpleNamespace(all_api_calls=calls)

    monkeypatch.setattr(refresh_module, "CALLS_DIR", str(calls_dir))
    monkeypatch.setattr(refresh_module, "load_manifest", lambda: manifest)
    monkeypatch.setattr(refresh_module, "load_gt", records)
    monkeypatch.setattr(
        refresh_module, "project_root", lambda path: path)
    monkeypatch.setattr(refresh_module, "analyze_project", analyze)
    monkeypatch.setattr(sys, "argv", ["refresh", "--all"])

    assert refresh_module.main() == 1
