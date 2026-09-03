## @package tests.test_failure_dispositions
#  Regression tests for ground-truth failure disposition classification.

import os
import sys

import ast
import pytest


SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from classify_ground_truth_failures import (  # noqa: E402
    DISPOSITION_ACCEPTED_UNKNOWN,
    DISPOSITION_FIX,
    DISPOSITION_GT,
    SOURCE_NON_SYNTACTIC_RECEIVER_TYPE,
    SOURCE_DYNAMIC_CALLABLE_ARGUMENT,
    SOURCE_INSTANCE_ATTRIBUTE_VALUE,
    SOURCE_UNRESOLVED_METHOD_ARGUMENT,
    SOURCE_PARAMETER_ATTRIBUTE_ITEM_EXTERNAL_CONTRACT,
    SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE,
    SCOPE_CONSERVATIVE,
    SCOPE_INTERPROC,
    SCOPE_LOCAL,
    SCOPE_SAME,
    build_entries,
    build_source_evidence,
    classify_disposition,
    is_primary_mismatch,
    record_key,
    release_blockers,
    render_jsonl,
    render_markdown,
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

    record["pcresolve_kind"] = "unknown"
    record["pcresolve_top_library"] = "unknown"
    disposition, scope, _ = classify_disposition(record)
    assert disposition == DISPOSITION_ACCEPTED_UNKNOWN
    assert scope == "evidence_limited_unknown"

    record["expression"] = "request.headers.get('Authorization')"
    disposition, _, _ = classify_disposition(record)
    assert disposition == DISPOSITION_FIX


def test_independent_boundary_review_accepts_only_honest_unknown():
    record = _record(
        pcresolve_kind="unknown", pcresolve_top_library="unknown")
    review = {
        "id": "external-result",
        "reason": "receiver is supplied only by an external API",
        "reviewed_by": "source-audit",
        "reviewed_at": "2026-08-30",
    }

    entries = build_entries(
        [record], boundary_reviews={record_key(record): review})

    assert entries[0]["disposition"] == DISPOSITION_ACCEPTED_UNKNOWN
    assert entries[0]["repair_scope"] == "evidence_limited_unknown"
    assert entries[0]["boundary_review_id"] == "external-result"

    record["pcresolve_kind"] = "local"
    record["pcresolve_top_library"] = "local"
    entries = build_entries(
        [record], boundary_reviews={record_key(record): review})
    assert entries[0]["disposition"] == DISPOSITION_FIX


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


def test_unreferenced_unbound_parameter_can_remain_unknown():
    record = _record(
        pcresolve_kind="unknown",
        pcresolve_top_library="unknown",
    )
    disposition, scope, _ = classify_disposition(
        record, SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)
    assert disposition == DISPOSITION_ACCEPTED_UNKNOWN
    assert scope == "evidence_limited_unknown"


def test_unreferenced_parameter_overclaim_must_drop_to_unknown():
    disposition, scope, _ = classify_disposition(
        _record(), SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_CONSERVATIVE


@pytest.mark.parametrize("source", [
    "def handler(value='text'):\n    value.strip()\n",
    "def handler(value: str):\n    value.strip()\n",
    "@register\ndef handler(value):\n    value.strip()\n",
    "class Handler:\n    def __init__(self, value):\n        value.strip()\n",
])
def test_declaration_evidence_or_implicit_entry_blocks_unbound_waiver(
        tmp_path, source):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "main.py").write_text(source, encoding="utf-8")
    call = next(node for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.Call)
                and ast.unparse(node) == "value.strip()")
    record = _record(lineno=call.lineno, col_offset=call.col_offset,
                     expression="value.strip()")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert evidence.get(record_key(record)) != (
        SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)


def test_unparsed_project_file_prevents_missing_reference_proof(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "main.py").write_text(
        "def handler(value):\n    value.strip()\n", encoding="utf-8")
    (project / "legacy.py").write_text(
        "print 'legacy syntax'\nhandler('text')\n", encoding="utf-8")
    record = _record(lineno=2, col_offset=4, expression="value.strip()")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert evidence.get(record_key(record)) != (
        SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)


def test_string_dispatch_reference_prevents_unbound_waiver(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "main.py").write_text(
        "def handler(value):\n    value.strip()\n"
        "globals()['handler']('text')\n", encoding="utf-8")
    record = _record(lineno=2, col_offset=4, expression="value.strip()")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert evidence.get(record_key(record)) != (
        SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)


def test_source_evidence_requires_no_reference_or_rebinding(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
def uncalled(value):
    return value.strip()

def called(value):
    return value.strip()

called('text')

def rebound(value):
    value = []
    return value.copy()

def self_assign(value):
    value = value.strip()
    return value

def table_only(value):
    return value.strip()

dispatch = {'handler': table_only}

def callback(value):
    return value.strip()

register(callback)

def later_rebind(value):
    result = value.strip()
    value = []
    return result
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    records = [
        _record(
            project="demo", file="main.py", lineno=2, col_offset=11,
            expression="value.strip()", pcresolve_kind="unknown",
            pcresolve_top_library="unknown"),
        _record(
            project="demo", file="main.py", lineno=5, col_offset=11,
            expression="value.strip()", pcresolve_kind="unknown",
            pcresolve_top_library="unknown"),
        _record(
            project="demo", file="main.py", lineno=11, col_offset=11,
            expression="value.copy()", pcresolve_kind="unknown",
            pcresolve_top_library="unknown"),
        _record(
            project="demo", file="main.py", lineno=14, col_offset=12,
            expression="value.strip()", pcresolve_kind="unknown",
            pcresolve_top_library="unknown"),
        _record(
            project="demo", file="main.py", lineno=18, col_offset=11,
            expression="value.strip()", pcresolve_kind="unknown",
            pcresolve_top_library="unknown"),
        _record(
            project="demo", file="main.py", lineno=23, col_offset=11,
            expression="value.strip()", pcresolve_kind="unknown",
            pcresolve_top_library="unknown"),
        _record(
            project="demo", file="main.py", lineno=28, col_offset=13,
            expression="value.strip()", pcresolve_kind="unknown",
            pcresolve_top_library="unknown"),
    ]
    evidence = build_source_evidence(
        records, {"demo": str(project)})
    assert evidence[record_key(records[0])] == (
        SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)
    assert record_key(records[1]) not in evidence
    assert record_key(records[2]) not in evidence
    assert evidence[record_key(records[3])] == (
        SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)
    assert record_key(records[4]) not in evidence
    assert record_key(records[5]) not in evidence
    assert evidence[record_key(records[6])] == (
        SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)


def test_parameter_attribute_item_requires_external_contract(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
def consume(frame):
    frame.loc[0].product().sum()

consume(make_frame())
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    inner = _record(
        project="demo", file="main.py", lineno=2, col_offset=4,
        expression="frame.loc[0].product().sum()",
        pcresolve_kind="unknown", pcresolve_top_library="unknown")
    evidence = build_source_evidence([inner], {"demo": str(project)})
    assert evidence[record_key(inner)] == (
        SOURCE_PARAMETER_ATTRIBUTE_ITEM_EXTERNAL_CONTRACT)


def test_project_attribute_assignment_keeps_item_receiver_fixable(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
class Frame:
    def __init__(self, payload):
        self.loc = payload

def consume(frame):
    frame.loc[0].product()

consume(Frame([]))
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    record = _record(
        project="demo", file="main.py", lineno=6, col_offset=4,
        expression="frame.loc[0].product()",
        pcresolve_kind="unknown", pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert record_key(record) not in evidence


def test_non_syntactic_receiver_requires_value_type_evidence(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
import external

def consume(value):
    value.reshape(1, -1)

consume(external.make_value())
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    record = _record(
        project="demo", file="main.py", lineno=4, col_offset=4,
        expression="value.reshape(1, -1)",
        pcresolve_kind="unknown", pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert evidence[record_key(record)] == (
        SOURCE_NON_SYNTACTIC_RECEIVER_TYPE)
    disposition, scope, _ = classify_disposition(
        record, evidence[record_key(record)])
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_INTERPROC


def test_source_evidence_matches_ast_normalized_expression(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
def clean(items):
    for item in items:
        item.replace('\\'', '').replace('{', '')
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    record = _record(
        project="demo", file="main.py", lineno=3, col_offset=8,
        expression="item.replace(\"'\", '').replace('{', '')",
        expected_kind="python", expected_top_library="python",
        pcresolve_kind="unknown", pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert evidence[record_key(record)] == (
        SOURCE_NON_SYNTACTIC_RECEIVER_TYPE)


def test_same_named_receiver_method_is_not_a_local_call_edge(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
def replace(group):
    group.mean()

replace(callback_value)
text.replace('-', ' ')
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    record = _record(
        project="demo", file="main.py", lineno=2, col_offset=4,
        expression="group.mean()", pcresolve_kind="unknown",
        pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert evidence[record_key(record)] == (
        SOURCE_NON_SYNTACTIC_RECEIVER_TYPE)


@pytest.mark.parametrize("source", [
    "value = []\nvalue.copy()\n",
    "def make():\n    return []\nvalue = make()\nvalue.copy()\n",
    "class Holder:\n    def __init__(self, value):\n"
    "        self.value = value\n    def run(self):\n"
    "        self.value.copy()\nHolder([]).run()\n",
    "def consume(value):\n    value.copy()\n"
    "alias = consume\nalias([])\n",
    "def consume(value):\n    value.copy()\n"
    "handlers = {'copy': consume}\nhandlers['copy']([])\n",
    "class Worker:\n    def __call__(self, value):\n"
    "        value.copy()\nWorker()([])\n",
])
def test_recoverable_flow_is_not_accepted_by_syntax_triage(tmp_path, source):
    project = tmp_path / "demo"
    project.mkdir()
    (project / "main.py").write_text(source, encoding="utf-8")
    call = next(node for node in ast.walk(ast.parse(source))
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "copy")
    record = _record(
        lineno=call.lineno, col_offset=call.col_offset,
        expression=ast.unparse(call), expected_kind="python",
        expected_top_library="python", pcresolve_kind="unknown",
        pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    disposition, _, _ = classify_disposition(
        record, evidence.get(record_key(record), ""))
    assert disposition == DISPOSITION_FIX


@pytest.mark.parametrize("evidence", [
    SOURCE_NON_SYNTACTIC_RECEIVER_TYPE,
    SOURCE_DYNAMIC_CALLABLE_ARGUMENT,
    SOURCE_INSTANCE_ATTRIBUTE_VALUE,
    SOURCE_UNRESOLVED_METHOD_ARGUMENT,
    SOURCE_PARAMETER_ATTRIBUTE_ITEM_EXTERNAL_CONTRACT,
])
def test_unreviewed_dependency_hint_does_not_pass_release_gate(evidence):
    record = _record(pcresolve_kind="unknown",
                     pcresolve_top_library="unknown")
    disposition, _, _ = classify_disposition(record, evidence)
    assert disposition == DISPOSITION_FIX
    assert release_blockers([{"disposition": disposition}])


def test_loop_body_rebinding_is_not_an_unbound_parameter_proof(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
def uncalled(value):
    for _ in range(2):
        value.copy()
        value = []
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    record = _record(lineno=3, col_offset=8, expression="value.copy()",
                     pcresolve_kind="unknown",
                     pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert evidence.get(record_key(record)) != (
        SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)


def test_for_iterable_evaluates_before_body_rebinding(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
def uncalled(value):
    for _ in range(value.dim()):
        value = []
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    record = _record(lineno=2, col_offset=19, expression="value.dim()",
                     pcresolve_kind="unknown",
                     pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert evidence[record_key(record)] == (
        SOURCE_UNBOUND_PARAMETER_NO_PROJECT_CALL_EDGE)


def test_direct_import_receiver_is_not_accepted_as_type_boundary(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = "import external\nexternal.run()\n"
    (project / "main.py").write_text(source, encoding="utf-8")
    record = _record(
        project="demo", file="main.py", lineno=2, col_offset=0,
        expression="external.run()", pcresolve_kind="unknown",
        pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert record_key(record) not in evidence


def test_local_constructor_method_is_not_accepted_as_type_boundary(tmp_path):
    project = tmp_path / "demo"
    project.mkdir()
    source = """\
class Worker:
    def run(self):
        return None

Worker().run()
"""
    (project / "main.py").write_text(source, encoding="utf-8")
    record = _record(
        project="demo", file="main.py", lineno=5, col_offset=0,
        expression="Worker().run()", expected_kind="local",
        expected_top_library="local", pcresolve_kind="unknown",
        pcresolve_top_library="unknown")
    evidence = build_source_evidence([record], {"demo": str(project)})
    assert record_key(record) not in evidence


@pytest.mark.parametrize("level", ["dynamic_probe", "manual_reasoned"])
def test_runtime_verification_is_not_a_static_boundary_proof(level):
    disposition, scope, _ = classify_disposition(_record(
        verification_level=level,
        pcresolve_kind="unknown",
        pcresolve_top_library="unknown",
    ))
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_INTERPROC
    assert release_blockers([{"disposition": disposition}])


def test_runtime_verification_does_not_prescribe_unknown():
    disposition, scope, _ = classify_disposition(_record(
        verification_level="dynamic_probe",
    ))
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_INTERPROC


def test_dynamic_local_callable_requires_independent_boundary_review():
    disposition, scope, _ = classify_disposition(_record(
        expected_kind="local",
        expected_top_library="local",
        pcresolve_kind="unknown",
        pcresolve_top_library="unknown",
        category="dynamic_local_callable",
        verification_level="manual_reasoned",
    ))
    assert disposition == DISPOSITION_FIX
    assert scope == SCOPE_LOCAL


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
    assert entries[0]["target_kind"] == "library"
    assert entries[0]["target_top_library"] == "numpy"
    assert entries[1]["target_kind"] == "library"
    assert entries[1]["target_top_library"] == "numpy"


def test_sidecar_is_sorted_and_deterministic():
    later = _record(lineno=2, expression="b.method()")
    earlier = _record(lineno=1, expression="a.method()")
    entries = build_entries([later, earlier])
    assert [entry["lineno"] for entry in entries] == [1, 2]
    assert render_jsonl(entries) == render_jsonl(entries)


def test_release_gate_allows_only_accepted_unknown():
    accepted = {"disposition": DISPOSITION_ACCEPTED_UNKNOWN}
    repair = {"disposition": DISPOSITION_FIX}
    correction = {"disposition": DISPOSITION_GT}
    assert release_blockers([accepted]) == []
    assert release_blockers([accepted, repair, correction]) == [
        repair, correction]


def test_markdown_lists_every_accepted_unknown_with_full_reason():
    entry = {
        "project": "demo",
        "file": "main.py",
        "lineno": 7,
        "col_offset": 4,
        "expression": "value.get('a|b')",
        "expected_kind": "library",
        "expected_top_library": "example",
        "pcresolve_kind": "unknown",
        "pcresolve_top_library": "unknown",
        "pcresolve_reason": "UNRESOLVED",
        "category": "transitive_method",
        "verification_level": "dynamic_probe",
        "source_evidence": SOURCE_NON_SYNTACTIC_RECEIVER_TYPE,
        "disposition": DISPOSITION_ACCEPTED_UNKNOWN,
        "repair_scope": "evidence_limited_unknown",
        "disposition_reason": "external return type|not in project source",
        "target_kind": "unknown",
        "target_top_library": "unknown",
    }

    report = render_markdown([entry])

    assert "## Accepted Unknown Details" in report
    assert "PCResolve's project-source-only static analysis contract" in report
    assert "1.0.5 pure-static contract" not in report
    assert "### demo (1)" in report
    assert "`main.py:7:4`" in report
    assert "`value.get('a\\|b')`" in report
    assert "`library / example`" in report
    assert "external return type\\|not in project source" in report
