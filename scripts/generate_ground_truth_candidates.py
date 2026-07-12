#!/usr/bin/env python3
## @package scripts.generate_ground_truth_candidates
#  Generate ground truth candidate JSONL from PCResolve output.
#
#  Reads ground_truth/projects.json and runs analyze_project() on each
#  project, writing one JSONL line per API call with fields pre-filled
#  from PCResolve.  Annotators fill in expected_* and status fields.
#  Manual GT entries (source="manual_gt") may be added for calls
#  PCResolve missed.
#
#  Usage:
#    python scripts/generate_ground_truth_candidates.py           # pilot only
#    python scripts/generate_ground_truth_candidates.py --all     # all projects
#    python scripts/generate_ground_truth_candidates.py --project click1

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve.cross_file import analyze_project


GT_DIR = os.path.join(os.path.dirname(__file__), "..", "ground_truth")
PROJECTS_FILE = os.path.join(GT_DIR, "projects.json")
CALLS_DIR = os.path.join(GT_DIR, "calls")


def _infer_expected_kind(top):
    if not top or top == "unknown":
        return "unknown"
    if top == "local":
        return "local"
    if top == "python":
        return "python"
    return "library"


def load_manifest():
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        return json.load(f)["projects"]


def project_root(rel_path):
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..", rel_path))


def relative_file(file_path, proj_root):
    try:
        return os.path.relpath(file_path, proj_root)
    except ValueError:
        return file_path


def generate_one(name, info):
    proj_root = project_root(info["path"])
    result = analyze_project(proj_root, scope_model="v2")

    calls = result.all_api_calls
    if not calls:
        return 0

    out_path = os.path.join(CALLS_DIR, name + ".jsonl")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for c in calls:
            rec = {
                "source": "pcresolve_candidate",
                "project": name,
                "file": relative_file(c.file_path, proj_root),
                "lineno": c.lineno,
                "col_offset": c.col_offset,
                "expression": c.expression,
                "pcresolve_kind": _infer_expected_kind(c.top_library),
                "pcresolve_top_library": c.top_library,
                "pcresolve_alternatives": c.alternatives,
                "pcresolve_decorated_by": c.decorated_by,
                "pcresolve_reason": c.reason,
                "pcresolve_confidence": c.confidence,
                "pcresolve_func_name": c.func_name,
                "expected_kind": "",
                "expected_top_library": "",
                "expected_alternatives": [],
                "expected_decorated_by": [],
                "status": "",
                "annotation_status": "draft",
                "category": "",
                "notes": "",
            }
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return len(calls)


def main():
    manifest = load_manifest()
    args = sys.argv[1:]

    selected = set()
    all_projects = "--all" in args
    for a in args:
        if a.startswith("--project="):
            selected.add(a.split("=", 1)[1])
        elif a == "--project" and args.index(a) + 1 < len(args):
            selected.add(args[args.index(a) + 1])

    os.makedirs(CALLS_DIR, exist_ok=True)

    total = 0
    for name, info in sorted(manifest.items()):
        if not all_projects and not selected and info.get("tier") != "pilot":
            continue
        if selected and name not in selected:
            continue
        proj_root = project_root(info["path"])
        if not os.path.isdir(proj_root):
            print("SKIP %s: path not found (%s)" % (name, proj_root))
            continue
        count = generate_one(name, info)
        total += count
        print("%-30s %4d calls" % (name, count))

    print("Total: %d calls across %s" % (total,
          "selected projects" if selected else
          "pilot projects" if not all_projects else "all projects"))


if __name__ == "__main__":
    main()
