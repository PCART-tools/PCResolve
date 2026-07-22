#!/usr/bin/env python3
## @package scripts.classify_ground_truth_failures
#  Classify locked ground-truth ownership mismatches into release dispositions.

import argparse
import collections
import json
import os
import sys


ROOT_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
GT_DIR = os.path.join(ROOT_DIR, "ground_truth")
CALLS_DIR = os.path.join(GT_DIR, "calls")
VERIFICATION_DIR = os.path.join(GT_DIR, "verification")
DEFAULT_JSONL = os.path.join(VERIFICATION_DIR, "failure-dispositions.jsonl")
DEFAULT_MARKDOWN = os.path.join(
    VERIFICATION_DIR, "failure-dispositions.md")

DISPOSITION_FIX = "fix_1_0_5"
DISPOSITION_BOUNDARY = "accepted_boundary"
DISPOSITION_GT = "ground_truth_correction"

SCOPE_CONSERVATIVE = "conservative_identity"
SCOPE_LOCAL = "local_identity"
SCOPE_SAME = "same_scope_result_protocol"
SCOPE_INTERPROC = "bounded_receiver_flow"
SCOPE_BOUNDARY = "documented_boundary"
SCOPE_GT = "label_correction"

_SAME_SCOPE_CATEGORIES = frozenset({
    "builtin",
    "builtin_callable",
    "builtin_container_method",
    "builtin_method_local_receiver",
    "builtin_string_method",
    "conversion_boundary",
    "direct_import",
    "library_result_boundary",
    "numpy_result_receiver",
    "numpy_scalar_receiver",
    "pandas_receiver_chain",
    "python_protocol_method",
    "regex_receiver",
})


## Return True when a locked positive record is a primary ownership mismatch.
#
#  @param record Ground-truth JSON object.
#  @return True for a current primary mismatch.
def is_primary_mismatch(record):
    if record.get("annotation_status") != "locked":
        return False
    if record.get("status") != "positive":
        return False
    expected = (
        record.get("expected_kind", ""),
        record.get("expected_top_library", ""),
    )
    actual = (
        record.get("pcresolve_kind", ""),
        record.get("pcresolve_top_library", ""),
    )
    return expected != actual


## Return whether a record is the documented Flask mapping payload boundary.
#
#  @param record Ground-truth JSON object.
#  @return True only for request.json.get calls in flask2.
def _is_flask_payload_boundary(record):
    return (
        record.get("project") == "flask2"
        and record.get("category") == "mapping_protocol_method"
        and record.get("expression", "").startswith("request.json.get(")
        and record.get("expected_kind") == "python"
        and record.get("pcresolve_top_library") == "flask"
    )


## Return whether a record has a GT label unsupported by its source program.
#
#  @param record Ground-truth JSON object.
#  @return True for the reviewed unreachable tensor-parameter records.
def _needs_dead_code_gt_correction(record):
    notes = record.get("verification_notes", "").lower()
    return (
        record.get("category") == "framework_tensor_receiver"
        and "unreachable" in notes
        and record.get("expected_kind") == "library"
    )


## Classify one primary mismatch into a release disposition and repair scope.
#
#  The disposition answers whether 1.0.5 must repair the record, retain a
#  documented boundary, or correct the GT label.  The repair scope groups
#  fixable records by implementation strategy without encoding library-name
#  whitelists.
#
#  @param record Ground-truth JSON object.
#  @return Tuple of disposition, repair scope, and explanation.
def classify_disposition(record):
    if _is_flask_payload_boundary(record):
        return (
            DISPOSITION_BOUNDARY,
            SCOPE_BOUNDARY,
            "framework payload mapping protocol boundary",
        )

    if _needs_dead_code_gt_correction(record):
        return (
            DISPOSITION_GT,
            SCOPE_GT,
            "unreachable parameter has no concrete owner in source",
        )

    expected_kind = record.get("expected_kind", "")
    category = record.get("category", "")

    if expected_kind == "unknown":
        return (
            DISPOSITION_FIX,
            SCOPE_CONSERVATIVE,
            "replace unsupported local/library certainty with unknown",
        )

    if expected_kind == "local":
        return (
            DISPOSITION_FIX,
            SCOPE_LOCAL,
            "protect project-local callable identity",
        )

    if category in _SAME_SCOPE_CATEGORIES:
        return (
            DISPOSITION_FIX,
            SCOPE_SAME,
            "propagate result or protocol ownership within local flow",
        )

    return (
        DISPOSITION_FIX,
        SCOPE_INTERPROC,
        "propagate receiver ownership through bounded project call evidence",
    )


## Load every JSONL record from the canonical calls directory.
#
#  @return List of ground-truth records.
def load_records():
    records = []
    for name in sorted(os.listdir(CALLS_DIR)):
        if not name.endswith(".jsonl"):
            continue
        path = os.path.join(CALLS_DIR, name)
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    records.append(json.loads(line))
    return records


## Build deterministic sidecar entries for current primary mismatches.
#
#  @param records Iterable of ground-truth records.
#  @return Sorted list of compact failure disposition dictionaries.
def build_entries(records):
    entries = []
    for record in records:
        if not is_primary_mismatch(record):
            continue
        disposition, repair_scope, explanation = classify_disposition(record)
        entries.append({
            "project": record.get("project", ""),
            "file": record.get("file", ""),
            "lineno": record.get("lineno", 0),
            "col_offset": record.get("col_offset", 0),
            "expression": record.get("expression", ""),
            "expected_kind": record.get("expected_kind", ""),
            "expected_top_library": record.get(
                "expected_top_library", ""),
            "pcresolve_kind": record.get("pcresolve_kind", ""),
            "pcresolve_top_library": record.get(
                "pcresolve_top_library", ""),
            "pcresolve_reason": record.get("pcresolve_reason", ""),
            "category": record.get("category", ""),
            "verification_level": record.get("verification_level", ""),
            "disposition": disposition,
            "repair_scope": repair_scope,
            "disposition_reason": explanation,
        })
    entries.sort(key=lambda item: (
        item["project"], item["file"], item["lineno"],
        item["col_offset"], item["expression"],
    ))
    return entries


## Serialize sidecar entries as deterministic JSONL.
#
#  @param entries Failure disposition entries.
#  @return UTF-8 JSONL text.
def render_jsonl(entries):
    return "".join(
        json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n"
        for entry in entries
    )


## Render a human-readable failure disposition summary.
#
#  @param entries Failure disposition entries.
#  @return Markdown report text.
def render_markdown(entries):
    disposition_counts = collections.Counter(
        entry["disposition"] for entry in entries)
    scope_counts = collections.Counter(
        entry["repair_scope"] for entry in entries)
    project_counts = collections.Counter(
        entry["project"] for entry in entries)
    category_counts = collections.Counter(
        entry["category"] for entry in entries)

    lines = [
        "# PCResolve 1.0.5 Failure Dispositions",
        "",
        "This report classifies every current locked primary ownership "
        "mismatch. The canonical call labels remain in `ground_truth/calls/`; "
        "the JSONL sidecar records release disposition only.",
        "",
        "## Release Disposition",
        "",
        "| Disposition | Records | Meaning |",
        "|---|---:|---|",
    ]
    meanings = {
        DISPOSITION_FIX: "Must be closed in 1.0.5",
        DISPOSITION_BOUNDARY: "Documented static-analysis boundary",
        DISPOSITION_GT: "Canonical GT label must be corrected",
    }
    for name in (
            DISPOSITION_FIX, DISPOSITION_BOUNDARY, DISPOSITION_GT):
        lines.append("| `%s` | %d | %s |" % (
            name, disposition_counts.get(name, 0), meanings[name]))
    lines.append("| **Total** | **%d** | |" % len(entries))

    lines.extend([
        "",
        "## Repair Scope",
        "",
        "| Repair scope | Records |",
        "|---|---:|",
    ])
    scope_order = (
        SCOPE_SAME,
        SCOPE_INTERPROC,
        SCOPE_CONSERVATIVE,
        SCOPE_LOCAL,
        SCOPE_BOUNDARY,
        SCOPE_GT,
    )
    for name in scope_order:
        lines.append("| `%s` | %d |" % (
            name, scope_counts.get(name, 0)))
    lines.append("| **Total** | **%d** |" % len(entries))

    lines.extend([
        "",
        "## Project Queue",
        "",
        "| Project | Records |",
        "|---|---:|",
    ])
    for name, count in sorted(
            project_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append("| `%s` | %d |" % (name, count))

    lines.extend([
        "",
        "## Failure Families",
        "",
        "| Category | Records |",
        "|---|---:|",
    ])
    for name, count in sorted(
            category_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append("| `%s` | %d |" % (name or "(none)", count))

    exceptional = [
        entry for entry in entries
        if entry["disposition"] != DISPOSITION_FIX
    ]
    lines.extend([
        "",
        "## Boundary And Label Records",
        "",
        "| Disposition | Location | Expression | Reason |",
        "|---|---|---|---|",
    ])
    for entry in exceptional:
        location = "%s/%s:%d:%d" % (
            entry["project"], entry["file"], entry["lineno"],
            entry["col_offset"])
        expression = entry["expression"].replace("|", "\\|")
        reason = entry["disposition_reason"].replace("|", "\\|")
        lines.append("| `%s` | `%s` | `%s` | %s |" % (
            entry["disposition"], location, expression, reason))

    lines.extend([
        "",
        "## Release Rule",
        "",
        "1. Every `fix_1_0_5` entry must either become a primary hit or be "
        "reclassified with reviewed evidence.",
        "2. `accepted_boundary` entries remain visible in the release report.",
        "3. `ground_truth_correction` entries must update the canonical GT "
        "before algorithm work continues.",
        "4. No mismatch may remain without a disposition.",
        "",
    ])
    return "\n".join(lines)


## Write or check generated disposition artifacts.
#
#  @param path Output file path.
#  @param content Expected file content.
#  @param check Whether to compare without writing.
#  @return True when the file matches or was written successfully.
def _write_or_check(path, content, check):
    if check:
        try:
            with open(path, encoding="utf-8") as stream:
                actual = stream.read()
        except OSError:
            print("MISSING: %s" % path)
            return False
        if actual != content:
            print("STALE: %s" % path)
            return False
        print("OK: %s" % path)
        return True
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
    print("Wrote: %s" % path)
    return True


## CLI entry point.
#  @return None; exits with status 1 when generated artifacts are stale.
def main():
    parser = argparse.ArgumentParser(
        description="Classify locked GT ownership failures")
    parser.add_argument(
        "--check", action="store_true",
        help="fail when generated disposition artifacts are stale")
    parser.add_argument("--jsonl", default=DEFAULT_JSONL)
    parser.add_argument("--markdown", default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    entries = build_entries(load_records())
    ok_json = _write_or_check(
        args.jsonl, render_jsonl(entries), args.check)
    ok_markdown = _write_or_check(
        args.markdown, render_markdown(entries), args.check)
    print("Classified %d primary mismatches" % len(entries))
    if not (ok_json and ok_markdown):
        sys.exit(1)


if __name__ == "__main__":
    main()
