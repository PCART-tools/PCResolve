#!/usr/bin/env python3
## @package scripts.evaluate_ground_truth
#  Evaluate PCResolve output against ground truth call annotations.
#
#  Reads ground_truth/calls/<project>.jsonl and runs analyze_project(),
#  compares each call record, and reports per-project and aggregate
#  precision/recall/ownership by expected_kind.
#
#  Usage:
#    python scripts/evaluate_ground_truth.py                                    # locked pilots only
#    python scripts/evaluate_ground_truth.py --include-draft                    # locked + reviewed/draft
#    python scripts/evaluate_ground_truth.py --include-unlocked                 # same as --include-draft
#    python scripts/evaluate_ground_truth.py --include-auto-labeled             # + auto_labeled in scoring
#    python scripts/evaluate_ground_truth.py --all                              # all projects
#    python scripts/evaluate_ground_truth.py --project click1

import json
import os
import sys
import warnings

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve.cross_file import analyze_project

warnings.filterwarnings("ignore", category=SyntaxWarning)

GT_DIR = os.path.join(os.path.dirname(__file__), "..", "ground_truth")
PROJECTS_FILE = os.path.join(GT_DIR, "projects.json")
CALLS_DIR = os.path.join(GT_DIR, "calls")


def _norm_path(p):
    return os.path.normpath(p).replace(os.sep, "/")


def _kind_from_top(top):
    if top == "local":
        return "local"
    if top == "python":
        return "python"
    if not top or top == "unknown":
        return "unknown"
    return "library"


def _kind_in_view(kind, view):
    if view == "all":
        return kind in ("library", "python", "local", "unknown")
    return kind == view


def load_manifest():
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        return json.load(f)["projects"]


def load_gt(project_name):
    path = os.path.join(CALLS_DIR, project_name + ".jsonl")
    if not os.path.exists(path):
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def project_root(rel_path):
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", rel_path))


def relative_file(file_path, proj_root):
    try:
        return _norm_path(os.path.relpath(file_path, proj_root))
    except ValueError:
        return _norm_path(file_path)


def pos_key(rec):
    """Position-only key: (project, file, lineno, col_offset)."""
    return (rec.get("project", ""),
            _norm_path(rec.get("file", "")),
            rec.get("lineno", 0),
            rec.get("col_offset", 0))


def _normalize_expr(expr):
    """Normalize an expression for cross-version comparison.

    Collapses whitespace and removes semantically irrelevant
    parentheses around comprehension targets that differ between
    Python 3.9 and 3.13 ast.unparse() output.  Example:
    `for (k, v)` and `for k, v` both normalize to `for k, v`.
    """
    import re
    s = re.sub(r"\s+", " ", expr).strip()
    # Remove parens around comprehension targets: for (x, y) → for x, y
    s = re.sub(r"\bfor\s+\(([^)]+)\)\s+in\b", r"for \1 in", s)
    return s


def match_position(gt_entries, pc_candidates):
    """One-to-one multiset match at a single (file, line, col) position.

    Consumes PC candidates so each is used at most once.  Returns a
    dict mapping GT-index → PC dict, and a list of unmatched PC
    candidates that can be reported as uncovered_prediction.
    """
    remaining = list(pc_candidates)
    matches = {}

    # Round 1: exact normalized-expression match, consuming candidates.
    for gt_index, gt in gt_entries:
        gt_norm = _normalize_expr(gt.get("expression", ""))
        for i, pc in enumerate(remaining):
            if _normalize_expr(pc.get("expression", "")) == gt_norm:
                matches[gt_index] = remaining.pop(i)
                break

    # Round 2: single-GT + single-PC unmatched → position fallback.
    if len(gt_entries) == 1 and len(pc_candidates) == 1 and not matches:
        matches[gt_entries[0][0]] = remaining.pop(0)

    return matches, remaining


def evaluate_one(name, info, view="all", include_auto_labeled=False):
    proj_root = project_root(info["path"])

    gt_records = load_gt(name)
    if not gt_records:
        return None

    result = analyze_project(proj_root)
    pc_by_pos = {}
    for c in result.all_api_calls:
        key = (name, relative_file(c.file_path, proj_root),
               c.lineno, c.col_offset)
        pc_by_pos.setdefault(key, []).append({
            "top_library": c.top_library,
            "kind": _kind_from_top(c.top_library),
            "alternatives": c.alternatives,
            "decorated_by": c.decorated_by,
            "reason": c.reason,
            "expression": c.expression,
        })

    # All GT positions (including draft/unscored) for uncovered tracking.
    all_gt = load_gt(name)
    covered_gt_positions = set(pos_key(r) for r in all_gt)

    # Build per-position matches (one-to-one multiset).
    # Group GT records by position, then match against PC candidates.
    gt_by_pos = {}
    for i, r in enumerate(gt_records):
        gt_by_pos.setdefault(pos_key(r), []).append((i, r))
    pos_matches = {}    # pos → {gt_index: pc_dict}
    unmatched_pc = {}   # pos → [remaining pc candidates]

    for pos, gt_entries in gt_by_pos.items():
        pcs = pc_by_pos.get(pos, [])
        matches, remaining = match_position(gt_entries, pcs)
        pos_matches[pos] = matches
        if remaining:
            unmatched_pc[pos] = remaining

    # By default only records that have been human-reviewed (reviewed/locked)
    # enter scoring.  auto_labeled and draft records are excluded to avoid
    # circular validation risk (auto-label copies pcresolve output).
    scorable_statuses = {"reviewed", "locked"}
    if include_auto_labeled:
        scorable_statuses.add("auto_labeled")

    included = []
    for r in gt_records:
        status = r.get("status", "")
        ek = r.get("expected_kind", "")
        ann = r.get("annotation_status", "")
        # Annotation gate: only reviewed/locked records enter scoring
        # by default (plus auto_labeled if --include-auto-labeled).
        # Negatives and unsupported also gate on annotation_status.
        if status in ("negative", "unsupported"):
            if ann in scorable_statuses:
                included.append(r)
            continue
        if ann not in scorable_statuses:
            continue
        if view == "all" and ek in ("library", "python", "local", "unknown"):
            included.append(r)
        elif view == "unknown" and ek == "unknown":
            included.append(r)
        elif view == "library" and ek == "library":
            included.append(r)
        elif view == "python" and ek == "python":
            included.append(r)
        elif view == "local" and ek == "local":
            included.append(r)

    metrics = {
        "project": name,
        "view": view,
        "records_total": len(gt_records),
        "records_scored": len(included),
        "auto_labeled": sum(
            1 for r in gt_records
            if r.get("annotation_status") == "auto_labeled"
        ),
        "awaiting_annotation": sum(
            1 for r in gt_records
            if r.get("annotation_status") == "draft"
            and not (r.get("expected_kind") and r.get("status"))
        ),
        "awaiting_review": sum(
            1 for r in gt_records
            if r.get("annotation_status") == "draft"
            and r.get("expected_kind") and r.get("status")
        ),
        "gt_total": len(included),
        "gt_positive": 0,
        "gt_negative": 0,
        "gt_ambiguous": 0,
        "gt_unsupported": 0,
        "primary_hit": 0,
        "candidate_hit": 0,
        "decorated_hit": 0,
        "primary_miss": 0,
        "decorated_miss": 0,
        "primary_identity_miss": 0,
        "false_positive": 0,
        "wrong_owner": 0,
        "uncovered_prediction": 0,
    }

    for idx, gt in enumerate(gt_records):
        if gt not in included:
            continue
        pos = pos_key(gt)
        matches = pos_matches.get(pos, {})
        pc = matches.get(idx)

        status = gt.get("status", "")
        if status not in ("positive", "negative", "ambiguous", "unsupported"):
            continue

        if status == "unsupported":
            metrics["gt_unsupported"] += 1
            continue

        expected_kind = gt.get("expected_kind", "")
        expected_top = gt.get("expected_top_library", "")
        expected_alts = gt.get("expected_alternatives", [])
        expected_deco = gt.get("expected_decorated_by", [])

        if pc is None:
            # GT record not found in current PCResolve output.
            if status == "positive":
                metrics["gt_positive"] += 1
                metrics["primary_miss"] += 1
            elif status == "negative":
                metrics["gt_negative"] += 1
            elif status == "ambiguous":
                metrics["gt_ambiguous"] += 1
            continue

        pc_top = pc["top_library"]
        pc_kind = pc["kind"]
        pc_alts = pc["alternatives"]
        pc_deco = pc["decorated_by"]

        if status == "negative":
            metrics["gt_negative"] += 1
            if _kind_in_view(pc_kind, view):
                metrics["false_positive"] += 1
            continue

        if status == "ambiguous":
            metrics["gt_ambiguous"] += 1
            continue

        # status == "positive"
        metrics["gt_positive"] += 1

        # Primary hit
        if pc_kind == expected_kind and pc_top == expected_top:
            metrics["primary_hit"] += 1
        elif expected_kind == "library" and expected_top in pc_alts:
            metrics["candidate_hit"] += 1
            metrics["primary_miss"] += 1
        else:
            metrics["primary_miss"] += 1

        # Decorated hit / miss
        if expected_deco:
            if all(d in pc_deco for d in expected_deco):
                if pc_kind == "local" and expected_kind == "local":
                    metrics["decorated_hit"] += 1
            else:
                metrics["decorated_miss"] += 1

        # Wrong owner: kind matches but owner is wrong and not in
        # expected_alternatives (annotator-acceptable alternatives).
        if (pc_kind == expected_kind
                and pc_kind == "library"
                and pc_top != expected_top
                and pc_top not in expected_alts):
            metrics["wrong_owner"] += 1

        # Primary identity miss: kind mismatch or unexpected local/python/unknown
        if pc_kind == expected_kind and pc_top != expected_top and expected_top not in pc_alts:
            metrics["primary_identity_miss"] += 1

    # Uncovered predictions: PC candidates that were not consumed
    # by any GT record during one-to-one matching, either because
    # the position has no GT at all or because there were more PC
    # candidates than GT records at that position.
    for pos, pcs in pc_by_pos.items():
        if pos not in covered_gt_positions:
            for pc in pcs:
                if _kind_in_view(pc["kind"], view):
                    metrics["uncovered_prediction"] += 1
        elif pos in unmatched_pc:
            for pc in unmatched_pc[pos]:
                if _kind_in_view(pc["kind"], view):
                    metrics["uncovered_prediction"] += 1

    tp = metrics["primary_hit"]
    fp = metrics["false_positive"] + metrics["wrong_owner"]
    fn = metrics["primary_miss"]
    total_pred = tp + fp
    total_true = tp + fn

    metrics["precision"] = round(tp / total_pred, 4) if total_pred > 0 else 0.0
    metrics["recall"] = round(tp / total_true, 4) if total_true > 0 else 0.0
    metrics["f1"] = round(2 * metrics["precision"] * metrics["recall"] / (metrics["precision"] + metrics["recall"]), 4) if (metrics["precision"] + metrics["recall"]) > 0 else 0.0

    return metrics


def print_project(m):
    if m is None:
        return
    if m["awaiting_annotation"] > 0 or m.get("awaiting_review", 0) > 0 or m.get("auto_labeled", 0) > 0:
        print("%-25s view=%-7s calls=%d scored=%d awaiting=%d review=%d auto=%d  gt=%3d pos=%3d neg=%2d  P=%.3f R=%.3f F1=%.3f  hit=%3d miss=%2d fp=%2d wrong=%2d deco=%d cand=%d ident=%d deco_m=%d uncov=%d" % (
            m["project"], m["view"], m["records_total"], m["records_scored"],
            m["awaiting_annotation"], m.get("awaiting_review", 0), m.get("auto_labeled", 0),
            m["gt_total"], m["gt_positive"], m["gt_negative"],
            m["precision"], m["recall"], m["f1"],
            m["primary_hit"], m["primary_miss"], m["false_positive"],
            m["wrong_owner"], m["decorated_hit"],
            m["candidate_hit"], m["primary_identity_miss"], m["decorated_miss"],
            m["uncovered_prediction"]))
    else:
        print("%-25s view=%-7s gt=%3d pos=%3d neg=%2d  P=%.3f R=%.3f F1=%.3f  hit=%3d miss=%2d fp=%2d wrong=%2d deco=%d cand=%d ident=%d deco_m=%d uncov=%d" % (
            m["project"], m["view"], m["gt_total"], m["gt_positive"], m["gt_negative"],
            m["precision"], m["recall"], m["f1"],
            m["primary_hit"], m["primary_miss"], m["false_positive"],
            m["wrong_owner"], m["decorated_hit"],
            m["candidate_hit"], m["primary_identity_miss"], m["decorated_miss"],
            m["uncovered_prediction"]))


def main():
    manifest = load_manifest()
    args = sys.argv[1:]

    view = "all"
    selected = set()
    all_projects = "--all" in args
    include_draft = ("--include-draft" in args
                     or "--include-unlocked" in args)
    include_auto_labeled = "--include-auto-labeled" in args
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith("--view="):
            view = a.split("=", 1)[1]
        elif a == "--view":
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                print("ERROR: --view requires a value", file=sys.stderr)
                sys.exit(1)
            i += 1
            view = args[i]
        elif a == "--all":
            pass
        elif a in ("--include-draft", "--include-unlocked", "--include-auto-labeled"):
            pass
        elif a.startswith("--project="):
            selected.add(a.split("=", 1)[1])
        elif a == "--project":
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                print("ERROR: --project requires a value", file=sys.stderr)
                sys.exit(1)
            i += 1
            selected.add(args[i])
        elif a in ("-h", "--help"):
            print("Usage: python scripts/evaluate_ground_truth.py [--all] [--include-draft|--include-unlocked] [--include-auto-labeled] [--project NAME] [--view all|library|python|local|unknown]")
            return
        i += 1

    if view not in ("all", "library", "python", "local", "unknown"):
        print("ERROR: --view must be one of: all, library, python, local, unknown", file=sys.stderr)
        sys.exit(1)

    total_gt = 0
    total_hit = 0
    total_miss = 0
    total_awaiting = 0
    total_awaiting_review = 0
    total_auto = 0
    total_records = 0
    total_scored = 0

    for name, info in sorted(manifest.items()):
        if not all_projects and not selected and info.get("tier") != "pilot":
            continue
        # Default: only locked projects.  Draft/reviewed projects need
        # --include-draft, --all, or explicit --project to enter scoring.
        if (not all_projects and not include_draft and not selected
                and info.get("status") != "locked"):
            continue
        if selected and name not in selected:
            continue
        proj_root = project_root(info["path"])
        if not os.path.isdir(proj_root):
            continue
        m = evaluate_one(name, info, view=view,
                         include_auto_labeled=include_auto_labeled)
        print_project(m)
        if m:
            total_gt += m["gt_positive"]
            total_hit += m["primary_hit"]
            total_miss += m["primary_miss"]
            total_awaiting += m.get("awaiting_annotation", 0)
            total_awaiting_review += m.get("awaiting_review", 0)
            total_auto += m.get("auto_labeled", 0)
            total_records += m.get("records_total", 0)
            total_scored += m.get("records_scored", 0)

    print("\nEvaluation coverage: records=%d scored=%d awaiting_annotation=%d"
          " awaiting_review=%d auto_labeled=%d"
          % (total_records, total_scored, total_awaiting,
             total_awaiting_review, total_auto))
    if total_awaiting > 0 or total_auto > 0 or total_awaiting_review > 0:
        if not include_auto_labeled and total_auto > 0:
            print("NOTE: %d auto_labeled records excluded (use --include-auto-labeled to score)"
                  % total_auto)
        if total_awaiting > 0:
            print("PROVISIONAL: %d records awaiting annotation" % total_awaiting)
        if total_awaiting_review > 0:
            print("PROVISIONAL: %d records have labels but await review" % total_awaiting_review)
        if include_auto_labeled and total_auto > 0:
            print("SELF-LABELED: auto_labeled records may reflect pcresolve output, not independent GT")
    if total_gt > 0:
        print("Aggregate: gt_positive=%d primary_hit=%d primary_miss=%d recall=%.3f" % (
            total_gt, total_hit, total_miss,
            total_hit / total_gt if total_gt > 0 else 0.0))


if __name__ == "__main__":
    main()
