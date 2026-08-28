#!/usr/bin/env python3
## @package scripts.refresh_ground_truth_snapshots
#  Refresh only PCResolve-owned fields in reviewed ground-truth records.

import argparse
import json
import os
import sys
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve.cross_file import analyze_project

from evaluate_ground_truth import (
    _kind_from_top,
    load_gt,
    load_manifest,
    match_position,
    pos_key,
    project_root,
    relative_file,
)

warnings.filterwarnings("ignore", category=SyntaxWarning)

CALLS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "ground_truth", "calls")

_PCRESOLVE_FIELDS = (
    "pcresolve_kind",
    "pcresolve_top_library",
    "pcresolve_alternatives",
    "pcresolve_decorated_by",
    "pcresolve_reason",
    "pcresolve_confidence",
    "pcresolve_func_name",
)


## Convert one ApiCall to the evaluator and snapshot representation.
#  @param project Logical ground-truth project name.
#  @param call ApiCall emitted by PCResolve.
#  @param root Analyzed project root.
#  @return Dict containing position, expression, and PCResolve fields.
def _call_candidate(project, call, root):
    return {
        "project": project,
        "file": relative_file(call.file_path, root),
        "lineno": call.lineno,
        "col_offset": call.col_offset,
        "expression": call.expression,
        "kind": _kind_from_top(call.top_library),
        "top_library": call.top_library,
        "alternatives": list(call.alternatives),
        "decorated_by": list(call.decorated_by),
        "reason": call.reason,
        "confidence": call.confidence,
        "func_name": call.func_name,
    }


## Return the PCResolve snapshot fields for a matched candidate.
#  @param candidate Evaluator-style candidate, or None for a missing call.
#  @return Dict limited to pcresolve_* keys.
def _snapshot(candidate):
    if candidate is None:
        return {
            "pcresolve_kind": "",
            "pcresolve_top_library": "",
            "pcresolve_alternatives": [],
            "pcresolve_decorated_by": [],
            "pcresolve_reason": "",
            "pcresolve_confidence": 0.0,
            "pcresolve_func_name": "",
        }
    return {
        "pcresolve_kind": candidate["kind"],
        "pcresolve_top_library": candidate["top_library"],
        "pcresolve_alternatives": candidate["alternatives"],
        "pcresolve_decorated_by": candidate["decorated_by"],
        "pcresolve_reason": candidate["reason"],
        "pcresolve_confidence": candidate["confidence"],
        "pcresolve_func_name": candidate["func_name"],
    }


## Refresh one project's PCResolve snapshot without changing GT labels.
#
#  Matching uses the evaluator's position-first, one-to-one multiset contract.
#  Human-owned fields, including expected_*, annotation status, verification
#  evidence, source, category, and notes, are copied unchanged.
#
#  @param project Logical ground-truth project name.
#  @param records Existing JSONL record dicts.
#  @param calls Current ApiCall objects.
#  @param root Analyzed project root.
#  @return Tuple of (refreshed records, changed record count, uncovered calls).
def refresh_records(project, records, calls, root):
    gt_by_pos = {}
    for index, record in enumerate(records):
        gt_by_pos.setdefault(pos_key(record), []).append((index, record))

    pc_by_pos = {}
    for call in calls:
        candidate = _call_candidate(project, call, root)
        pc_by_pos.setdefault(pos_key(candidate), []).append(candidate)

    matches = {}
    uncovered = []
    for position in set(gt_by_pos) | set(pc_by_pos):
        position_matches, remaining = match_position(
            gt_by_pos.get(position, []), pc_by_pos.get(position, []))
        matches.update(position_matches)
        uncovered.extend(remaining)

    refreshed = []
    changed = 0
    for index, record in enumerate(records):
        updated = dict(record)
        values = _snapshot(matches.get(index))
        record_changed = any(
            updated.get(field) != values[field]
            for field in _PCRESOLVE_FIELDS)
        updated.update(values)
        refreshed.append(updated)
        if record_changed:
            changed += 1
    return refreshed, changed, uncovered


## Write JSONL records with stable UTF-8 and LF line endings.
#  @param path Output JSONL path.
#  @param records Record dicts to write.
def _write_jsonl(path, records):
    with open(path, "w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")


## Parse command-line arguments.
#  @return argparse Namespace.
def _parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Refresh pcresolve_* fields while preserving reviewed GT labels."))
    parser.add_argument(
        "--all", action="store_true", help="refresh every manifest project")
    parser.add_argument(
        "--project", action="append", default=[], metavar="NAME",
        help="refresh one project; may be repeated")
    parser.add_argument(
        "--check", action="store_true",
        help="fail if snapshots are stale; do not write files")
    return parser.parse_args()


## CLI entry point.
#  @return Process exit code.
def main():
    args = _parse_args()
    manifest = load_manifest()
    selected = set(args.project)
    unknown = sorted(selected - set(manifest))
    if unknown:
        print("ERROR: unknown project(s): %s" % ", ".join(unknown),
              file=sys.stderr)
        return 1

    if args.all:
        names = sorted(manifest)
    elif selected:
        names = sorted(selected)
    else:
        names = sorted(
            name for name, info in manifest.items()
            if info.get("status") == "locked")

    failures = 0
    total_changed = 0
    for name in names:
        info = manifest[name]
        root = project_root(info["path"])
        records = load_gt(name)
        if not records:
            print("SKIP %-25s no GT records" % name)
            continue
        if not os.path.isdir(root):
            print("ERROR: project path missing for %s: %s" % (name, root),
                  file=sys.stderr)
            failures += 1
            continue

        result = analyze_project(root)
        refreshed, changed, uncovered = refresh_records(
            name, records, result.all_api_calls, root)
        if uncovered:
            print("ERROR: %-25s %d uncovered prediction(s)" % (
                name, len(uncovered)), file=sys.stderr)
            failures += 1
            continue

        total_changed += changed
        if changed:
            if args.check:
                failures += 1
            else:
                _write_jsonl(
                    os.path.join(CALLS_DIR, name + ".jsonl"), refreshed)
        state = "STALE" if changed and args.check else "UPDATED" if changed else "OK"
        print("%-25s changed=%4d [%s]" % (name, changed, state))

    print("Snapshot records changed: %d" % total_changed)
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
