#!/usr/bin/env python3
## @package scripts.evaluate_ground_truth
#  Evaluate PCResolve output against ground truth call annotations.
#
#  Reads ground_truth/calls/<project>.jsonl and runs analyze_project(),
#  compares each call record, and reports per-project and aggregate
#  precision/recall/ownership by expected_kind.
#
#  Usage:
#    python scripts/evaluate_ground_truth.py                    # pilot only
#    python scripts/evaluate_ground_truth.py --all               # all projects
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
        return kind in ("library", "python", "local")
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


def match_key(rec):
    return (rec.get("project", ""),
            _norm_path(rec.get("file", "")),
            rec.get("lineno", 0),
            rec.get("col_offset", 0),
            rec.get("expression", ""))


def evaluate_one(name, info, view="all"):
    proj_root = project_root(info["path"])

    gt_records = load_gt(name)
    if not gt_records:
        return None

    result = analyze_project(proj_root, scope_model="v2")
    pc_calls = {}
    for c in result.all_api_calls:
        key = (name, relative_file(c.file_path, proj_root),
               c.lineno, c.col_offset, c.expression)
        pc_calls[key] = {
            "top_library": c.top_library,
            "kind": _kind_from_top(c.top_library),
            "alternatives": c.alternatives,
            "decorated_by": c.decorated_by,
            "reason": c.reason,
        }

    # All GT keys (including draft) for uncovered-prediction tracking.
    covered_gt_keys = set(match_key(r) for r in gt_records)

    included = []
    for r in gt_records:
        status = r.get("status", "")
        ek = r.get("expected_kind", "")
        # Negatives and unsupported always enter scoring; their view
        # relevance is decided by _kind_in_view on the pc side.
        if status in ("negative", "unsupported"):
            included.append(r)
        elif view == "all" and ek in ("library", "python", "local"):
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

    for gt in included:
        key = match_key(gt)
        pc = pc_calls.get(key)

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

    # Uncovered predictions: PCResolve output not covered by ANY GT
    # record (including draft/unscored).  Does NOT enter P/R/F1;
    # tracked as annotation-coverage risk until GT is reviewed/locked.
    for key, pc in pc_calls.items():
        if key in covered_gt_keys:
            continue
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
    print("%-25s view=%-7s gt=%3d pos=%3d neg=%2d  P=%.3f R=%.3f F1=%.3f  hit=%3d miss=%2d fp=%2d wrong=%2d deco=%d cand=%d ident=%d deco_m=%d uncov=%d" % (
        m["project"], m["view"], m["gt_total"], m["gt_positive"], m["gt_negative"],
        m["precision"], m["recall"], m["f1"],
        m["primary_hit"], m["primary_miss"], m["false_positive"],
        m["wrong_owner"], m["decorated_hit"],
        m["candidate_hit"], m["primary_identity_miss"], m["decorated_miss"],
        m["uncovered_prediction"]))  # annotation coverage risk only


def main():
    manifest = load_manifest()
    args = sys.argv[1:]

    view = "all"
    selected = set()
    all_projects = "--all" in args
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
        elif a.startswith("--project="):
            selected.add(a.split("=", 1)[1])
        elif a == "--project":
            if i + 1 >= len(args) or args[i + 1].startswith("--"):
                print("ERROR: --project requires a value", file=sys.stderr)
                sys.exit(1)
            i += 1
            selected.add(args[i])
        elif a in ("-h", "--help"):
            print("Usage: python scripts/evaluate_ground_truth.py [--all] [--project NAME] [--view all|library|python|local]")
            return
        i += 1

    if view not in ("all", "library", "python", "local"):
        print("ERROR: --view must be one of: all, library, python, local", file=sys.stderr)
        sys.exit(1)

    total_gt = 0
    total_hit = 0
    total_miss = 0

    for name, info in sorted(manifest.items()):
        if not all_projects and not selected and info.get("tier") != "pilot":
            continue
        if selected and name not in selected:
            continue
        proj_root = project_root(info["path"])
        if not os.path.isdir(proj_root):
            continue
        m = evaluate_one(name, info, view=view)
        print_project(m)
        if m:
            total_gt += m["gt_positive"]
            total_hit += m["primary_hit"]
            total_miss += m["primary_miss"]

    if total_gt > 0:
        print("\nAggregate: gt_positive=%d primary_hit=%d primary_miss=%d recall=%.3f" % (
            total_gt, total_hit, total_miss,
            total_hit / total_gt if total_gt > 0 else 0.0))


if __name__ == "__main__":
    main()
