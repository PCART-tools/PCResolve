## @package tests.test_failure_dispositions
#  Regression tests for ground-truth failure disposition classification.

import os
import sys


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from classify_ground_truth_failures import (  # noqa: E402
    DISPOSITION_ACCEPTED_UNKNOWN,
    DISPOSITION_FIX,
    DISPOSITION_GT,
    SCOPE_CONSERVATIVE,
    SCOPE_INTERPROC,
    SCOPE_LOCAL,
    SCOPE_SAME,
    build_entries,
    classify_disposition,
    is_primary_mismatch,
    render_jsonl,
)


def _record(**overrides):
    record = {
        "project": "demo",
        "file": "main.py",
        "lineno": 1,
        "col_offset": 0,
        "expression": "value.method()",
        "expected_kind": "library",
        "expected_top_library": "numpy",
        "pcresolve_kind": "local",
        "pcresolve_top_library": "local",
        "pcresolve_reason": "LOCAL_DEFINITION",
        "status": "positive",
        "annotation_status": "locked",
        "category": "numpy_array_receiver",
        "verification_level": "static_context",
        "verification_notes": "receiver is a NumPy array",
    }
    record.update(overrides)
    return record


def test_only_locked_positive_primary_mismatches_are_classified():
    assert is_primary_mismatch(_record())
    assert not is_primary_mismatch(_record(annotation_status="draft"))
    assert not is_primary_mismatch(_record(status="unsupported"))
    assert not is_primary_mismatch(_record(
        pcresolve_kind="library", pcresolve_top_library="numpy"))


def test_flask_payload_boundary_requires_conservative_unknown():
    record = _record(
        project="flask2",
        expression="request.json.get('title')",
        category="mapping_protocol_method",
        expected_kind="python",
        expected_top_library="python",
        pcresolve_kind="library",
        pcresolve_top_library="flask",
    )
    disposition, scope, _ = classify_disposition(record)
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_CONSERVATIVE

    record["expression"] = "request.headers.get('Authorization')"
    disposition, _, _ = classify_disposition(record)
    assert disposition == DISPOSITION_FIX


def test_unreachable_tensor_parameter_requests_gt_correction():
    record = _record(
        category="framework_tensor_receiver",
        expected_top_library="torch",
        verification_notes="call unreachable in source",
    )
    disposition, scope, _ = classify_disposition(record)
    assert disposition == DISPOSITION_GT
    assert scope == "label_correction"


def test_expected_unknown_prioritizes_conservative_identity():
    disposition, scope, _ = classify_disposition(_record(
        expected_kind="unknown",
        expected_top_library="unknown",
        category="file_like_parameter",
    ))
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_CONSERVATIVE


def test_expected_local_prioritizes_local_identity():
    disposition, scope, _ = classify_disposition(_record(
        expected_kind="local",
        expected_top_library="local",
        category="local_method",
    ))
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_LOCAL


def test_protocol_family_uses_same_scope_repair():
    disposition, scope, _ = classify_disposition(_record(
        expected_kind="python",
        expected_top_library="python",
        category="builtin_string_method",
    ))
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_SAME


def test_receiver_family_uses_bounded_interprocedural_repair():
    disposition, scope, _ = classify_disposition(_record())
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_INTERPROC


def test_runtime_only_owner_is_accepted_when_result_is_unknown():
    disposition, scope, _ = classify_disposition(_record(
        verification_level="dynamic_probe",
        pcresolve_kind="unknown",
        pcresolve_top_library="unknown",
    ))
    assert disposition == DISPOSITION_ACCEPTED_UNKNOWN
    assert scope == "evidence_limited_unknown"


def test_runtime_only_owner_drops_unsupported_local_certainty():
    disposition, scope, _ = classify_disposition(_record(
        verification_level="dynamic_probe",
    ))
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_CONSERVATIVE


def test_dynamic_local_callable_can_remain_unknown():
    disposition, scope, _ = classify_disposition(_record(
        expected_kind="local",
        expected_top_library="local",
        pcresolve_kind="unknown",
        pcresolve_top_library="unknown",
        category="dynamic_local_callable",
        verification_level="manual_reasoned",
    ))
    assert disposition == DISPOSITION_ACCEPTED_UNKNOWN
    assert scope == "evidence_limited_unknown"


def test_ambiguous_monkey_patch_can_remain_unknown():
    disposition, scope, _ = classify_disposition(_record(
        expected_kind="local",
        expected_top_library="local",
        pcresolve_kind="unknown",
        pcresolve_top_library="unknown",
        category="monkey_patched_local_method",
        verification_level="static_context",
    ))
    assert disposition == DISPOSITION_ACCEPTED_UNKNOWN
    assert scope == "evidence_limited_unknown"


def test_runtime_branch_overclaim_must_become_unknown():
    disposition, scope, _ = classify_disposition(_record(
        expected_kind="unknown",
        expected_top_library="unknown",
        pcresolve_kind="library",
        pcresolve_top_library="gzip",
        category="branch_dependent_io_receiver",
        verification_level="manual_reasoned",
    ))
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_CONSERVATIVE


def test_sidecar_records_release_target():
    runtime_unknown = _record(
        verification_level="dynamic_probe",
        pcresolve_kind="unknown",
        pcresolve_top_library="unknown",
    )
    runtime_overclaim = _record(
        lineno=2,
        verification_level="dynamic_probe",
    )
    entries = build_entries([runtime_unknown, runtime_overclaim])
    assert entries[0]["target_kind"] == "unknown"
    assert entries[0]["target_top_library"] == "unknown"
    assert entries[1]["target_kind"] == "unknown"
    assert entries[1]["target_top_library"] == "unknown"


def test_sidecar_is_sorted_and_deterministic():
    later = _record(lineno=2, expression="b.method()")
    earlier = _record(lineno=1, expression="a.method()")
    entries = build_entries([later, earlier])
    assert [entry["lineno"] for entry in entries] == [1, 2]
    assert render_jsonl(entries) == render_jsonl(entries)
