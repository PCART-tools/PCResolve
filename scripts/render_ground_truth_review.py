#!/usr/bin/env python3
## @package scripts.render_ground_truth_review
#  Generate human-audit Markdown views from canonical GT JSONL.
#
#  Reads ground_truth/projects.json and ground_truth/calls/*.jsonl,
#  produces ground_truth/review/ with per-project grouped views.
#  Does NOT modify canonical JSONL.
#
#  Grouping:
#    - Per verification_level: static_obvious, static_context,
#      dynamic_probe, manual_reasoned -> <project>/<level>.md
#    - suspicious.md: cross-cutting view of records needing attention
#
#  Usage:
#    python scripts/render_ground_truth_review.py
#    python scripts/render_ground_truth_review.py --project hfhd

import argparse
import json
import os
import shutil
import sys
from collections import Counter

GT_DIR = os.path.join(os.path.dirname(__file__), "..", "ground_truth")
CALLS_DIR = os.path.join(GT_DIR, "calls")
PROJECTS_FILE = os.path.join(GT_DIR, "projects.json")
REVIEW_DIR = os.path.join(GT_DIR, "review")

LEVEL_MD_ORDER = ["static_obvious", "static_context", "dynamic_probe",
                  "manual_reasoned"]

# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------

def _md_escape(text):
    """Escape pipe and backtick for Markdown table cells."""
    return text.replace("|", "\\|").replace("`", "\\`")


def _render_record_table(records):
    """Render a Markdown table of GT records."""
    if not records:
        return "*No records.*\n"

    lines = []
    header = ("| File:Line:Col | Expression | GT | PCResolve | "
              "Category | Level | Notes |")
    sep = ("|---------------|------------|----|-----------|"
           "----------|-------|-------|")
    lines.append(header)
    lines.append(sep)

    for r in records:
        pos = "%s:%d:%d" % (r.get("file", ""),
                            r.get("lineno", 0),
                            r.get("col_offset", 0))
        expr = _md_escape(r.get("expression", ""))
        if len(expr) > 70:
            expr = expr[:67] + "..."

        gt = "%s / %s" % (r.get("expected_kind", ""),
                          r.get("expected_top_library", ""))
        pc = "%s / %s" % (r.get("pcresolve_kind", ""),
                          r.get("pcresolve_top_library", ""))
        cat = r.get("category", "") or "-"
        level = r.get("verification_level", "") or "-"
        notes_cell = ""
        if r.get("notes"):
            notes_cell += "gt: " + _md_escape(r["notes"][:80])
        if r.get("verification_notes"):
            if notes_cell:
                notes_cell += "<br>"
            notes_cell += "v: " + _md_escape(r["verification_notes"][:80])

        lines.append("| %s | `%s` | %s | %s | %s | %s | %s |" % (
            pos, expr, gt, pc, cat, level, notes_cell))

    return "\n".join(lines) + "\n"


def _count_by_level(records):
    c = Counter(r.get("verification_level", "?") for r in records)
    return c


def _count_suspicious(records):
    """Count records matching suspicious criteria."""
    count = 0
    for r in records:
        if _is_suspicious(r):
            count += 1
    return count


def _is_suspicious(r):
    """Check if a single record matches any suspicious criterion."""
    ek = r.get("expected_kind", "")
    etl = r.get("expected_top_library", "")
    pck = r.get("pcresolve_kind", "")
    pctl = r.get("pcresolve_top_library", "")
    palts = r.get("pcresolve_alternatives", []) or []
    edeco = r.get("expected_decorated_by", []) or []
    pdeco = r.get("pcresolve_decorated_by", []) or []
    level = r.get("verification_level", "")
    status = r.get("status", "")

    if pck and ek and pck != ek:
        return True
    if pctl and etl and pctl != etl and etl not in palts:
        return True
    if ek == "library" and pck and pck != "library":
        return True
    if edeco and not all(d in pdeco for d in edeco):
        return True
    if level in ("manual_reasoned", "unsupported"):
        return True
    if status in ("ambiguous", "unsupported"):
        return True
    return False


def _suspicious_reasons(r):
    """Return list of reason strings for a suspicious record."""
    reasons = []
    ek = r.get("expected_kind", "")
    etl = r.get("expected_top_library", "")
    pck = r.get("pcresolve_kind", "")
    pctl = r.get("pcresolve_top_library", "")
    palts = r.get("pcresolve_alternatives", []) or []
    edeco = r.get("expected_decorated_by", []) or []
    pdeco = r.get("pcresolve_decorated_by", []) or []
    level = r.get("verification_level", "")
    status = r.get("status", "")

    if pck and ek and pck != ek:
        reasons.append("kind mismatch: expected=%s pcresolve=%s" % (ek, pck))
    if pctl and etl and pctl != etl and etl not in palts:
        reasons.append("owner mismatch: expected=%s pcresolve=%s" % (etl, pctl))
    if ek == "library" and pck and pck != "library":
        reasons.append("expected library, pcresolve=%s" % pck)
    if edeco and not all(d in pdeco for d in edeco):
        missing = [d for d in edeco if d not in pdeco]
        reasons.append("decorated_by missing: %s" % ", ".join(missing))
    if level in ("manual_reasoned", "unsupported"):
        reasons.append("verification_level=%s" % level)
    if status in ("ambiguous", "unsupported"):
        reasons.append("status=%s" % status)
    return reasons


# ---------------------------------------------------------------------------
# Project overview
# ---------------------------------------------------------------------------

def _render_overview(proj_name, records, manifest_info):
    """Generate overview.md for a project."""
    lines = []
    lines.append("# %s — Ground Truth Overview" % proj_name)
    lines.append("")
    lines.append("**Status:** %s  |  **Tier:** %s  |  **Calls:** %d"
                 % (manifest_info.get("status", "?"),
                    manifest_info.get("tier", "?"),
                    len(records)))
    lines.append("")

    # Annotation status distribution
    ann_statuses = Counter(r.get("annotation_status", "?") for r in records)
    lines.append("## Annotation Status")
    lines.append("")
    for s, n in sorted(ann_statuses.items()):
        lines.append("- %s: %d" % (s, n))
    lines.append("")

    # Status distribution
    statuses = Counter(r.get("status", "?") for r in records)
    lines.append("## Call Status")
    lines.append("")
    for s in ["positive", "negative", "ambiguous", "unsupported"]:
        if statuses.get(s):
            lines.append("- %s: %d" % (s, statuses[s]))
    lines.append("")

    # Kind distribution
    kinds = Counter(r.get("expected_kind", "?") for r in records)
    lines.append("## Expected Kind")
    lines.append("")
    for k in ["library", "python", "local", "unknown"]:
        if kinds.get(k):
            lines.append("- %s: %d" % (k, kinds[k]))
    lines.append("")

    # Verification level breakdown
    levels = _count_by_level(records)
    lines.append("## Verification Level Breakdown")
    lines.append("")
    for lvl in LEVEL_MD_ORDER + ["unsupported"]:
        if levels.get(lvl):
            lines.append("- [%s](%s.md): %d" % (lvl, lvl, levels[lvl]))
    lines.append("")

    # Suspicious count
    sus_count = _count_suspicious(records)
    lines.append("## [Suspicious Records](suspicious.md): %d" % sus_count)
    lines.append("")

    # Category breakdown
    cats = Counter(r.get("category", "") or "(none)" for r in records)
    lines.append("## Category Breakdown")
    lines.append("")
    for cat, n in sorted(cats.items()):
        lines.append("- %s: %d" % (cat, n))
    lines.append("")

    # Top libraries
    libs = Counter()
    for r in records:
        if r.get("expected_kind") == "library":
            libs[r.get("expected_top_library", "?")] += 1
    if libs:
        lines.append("## Top Libraries")
        lines.append("")
        for lib, n in libs.most_common(20):
            lines.append("- %s: %d" % (lib, n))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-level views
# ---------------------------------------------------------------------------

def _render_level_view(proj_name, level, records):
    """Generate <level>.md for a set of records."""
    lines = []
    lines.append("# %s — %s (%d records)" % (proj_name, level, len(records)))
    lines.append("")
    lines.append(_render_record_table(records))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Suspicious view
# ---------------------------------------------------------------------------

def _render_suspicious_view(proj_name, records):
    """Generate suspicious.md — one row per record with Reasons column."""
    suspicious = [(r, _suspicious_reasons(r))
                  for r in records if _is_suspicious(r)]
    if not suspicious:
        return "# %s — Suspicious Records\n\n*No suspicious records.*\n" % proj_name

    lines = []
    lines.append("# %s — Suspicious Records (%d)" % (proj_name, len(suspicious)))
    lines.append("")
    lines.append("Each record appears once.  The **Reasons** column lists all")
    lines.append("matching suspicious criteria.")
    lines.append("")

    header = ("| File:Line:Col | Expression | GT | PCResolve | "
              "Category | Level | Reasons |")
    sep = ("|---------------|------------|----|-----------|"
           "----------|-------|---------|")
    lines.append(header)
    lines.append(sep)

    for r, reasons in sorted(suspicious,
                             key=lambda x: (x[0].get("file", ""),
                                            x[0].get("lineno", 0))):
        pos = "%s:%d:%d" % (r.get("file", ""),
                            r.get("lineno", 0),
                            r.get("col_offset", 0))
        expr = _md_escape(r.get("expression", ""))
        if len(expr) > 60:
            expr = expr[:57] + "..."

        gt = "%s / %s" % (r.get("expected_kind", ""),
                          r.get("expected_top_library", ""))
        pc = "%s / %s" % (r.get("pcresolve_kind", ""),
                          r.get("pcresolve_top_library", ""))
        cat = r.get("category", "") or "-"
        level = r.get("verification_level", "") or "-"
        reasons_cell = "<br>".join(_md_escape(re) for re in reasons)

        lines.append("| %s | `%s` | %s | %s | %s | %s | %s |" % (
            pos, expr, gt, pc, cat, level, reasons_cell))

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

def _render_index(project_results):
    """Generate index.md with aggregate overview."""
    lines = []
    lines.append("# Ground Truth Review Views")
    lines.append("")
    lines.append("Generated by: `scripts/render_ground_truth_review.py`")
    lines.append("")
    lines.append("Human-audit views from canonical GT JSONL records.")
    lines.append("Canonical JSONL files in `ground_truth/calls/` remain the")
    lines.append("machine source of truth.")
    lines.append("")

    lines.append("## Pilot Summary")
    lines.append("")
    lines.append("| Project | Calls | Status | static_obvious | "
                 "static_context | dynamic_probe | manual_reasoned | Suspicious |")
    lines.append("|---------|-------|--------|---------------|"
                 "---------------|--------------|-----------------|------------|")
    total_calls = 0
    total_sus = 0
    total_levels = Counter()
    for proj_name, records, manifest_info in project_results:
        levels = _count_by_level(records)
        sus = _count_suspicious(records)
        total_calls += len(records)
        total_sus += sus
        total_levels.update(levels)
        lines.append("| [%s](%s/overview.md) | %d | %s | %d | %d | %d | %d | %d |"
                     % (proj_name, proj_name, len(records),
                        manifest_info.get("status", "?"),
                        levels.get("static_obvious", 0),
                        levels.get("static_context", 0),
                        levels.get("dynamic_probe", 0),
                        levels.get("manual_reasoned", 0),
                        sus))
    lines.append("| **TOTAL** | **%d** | | **%d** | **%d** | **%d** | **%d** | **%d** |"
                 % (total_calls,
                    total_levels.get("static_obvious", 0),
                    total_levels.get("static_context", 0),
                    total_levels.get("dynamic_probe", 0),
                    total_levels.get("manual_reasoned", 0),
                    total_sus))
    lines.append("")

    lines.append("## Directory Layout")
    lines.append("")
    lines.append("```")
    lines.append("ground_truth/review/")
    lines.append("  index.md")
    for proj_name, _, _ in project_results:
        lines.append("  %s/" % proj_name)
        lines.append("    overview.md")
        for lvl in LEVEL_MD_ORDER:
            lines.append("    %s.md" % lvl)
        lines.append("    suspicious.md")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate human-audit Markdown views from GT JSONL")
    parser.add_argument("--project", action="append", default=[],
                        help="Only render this project (repeatable)")
    ns = parser.parse_args()

    with open(PROJECTS_FILE, encoding="utf-8") as f:
        manifest = json.load(f)["projects"]

    # All reviewed/locked pilots (for index.md always)
    all_pilot_names = [n for n, info in manifest.items()
                       if info.get("tier") == "pilot"
                       and info.get("status") in ("reviewed", "locked")]

    if ns.project:
        selected_names = [n for n in all_pilot_names if n in ns.project]
        unknown = [n for n in ns.project if n not in set(manifest.keys())]
        non_pilot = [n for n in ns.project
                     if n in manifest and manifest[n].get("tier") != "pilot"]
        if unknown:
            for name in unknown:
                print("ERROR: unknown project '%s'" % name, file=sys.stderr)
            return 1
        if non_pilot:
            for name in non_pilot:
                print("ERROR: '%s' is not a pilot project (tier='%s')"
                      % (name, manifest[name].get("tier", "?")),
                      file=sys.stderr)
            return 1
        if not selected_names:
            print("ERROR: no pilot projects selected", file=sys.stderr)
            return 1
    else:
        selected_names = list(all_pilot_names)
        # Full run: clean entire review dir to remove stale project dirs
        if os.path.exists(REVIEW_DIR):
            shutil.rmtree(REVIEW_DIR)

    # Load ALL pilot records for index.md
    all_project_results = []
    for name in all_pilot_names:
        path = os.path.join(CALLS_DIR, name + ".jsonl")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        all_project_results.append((name, records, manifest[name]))

    # Load selected project records for per-project views
    selected_results = []
    for name in selected_names:
        path = os.path.join(CALLS_DIR, name + ".jsonl")
        if not os.path.exists(path):
            print("SKIP %s: JSONL not found" % name, file=sys.stderr)
            continue
        with open(path, encoding="utf-8") as f:
            records = [json.loads(line) for line in f if line.strip()]
        selected_results.append((name, records, manifest[name]))

    # Ensure review dir exists
    os.makedirs(REVIEW_DIR, exist_ok=True)

    # Generate index from ALL pilots (always)
    index_text = _render_index(all_project_results)
    with open(os.path.join(REVIEW_DIR, "index.md"), "w", encoding="utf-8") as f:
        f.write(index_text)
    print("Wrote: review/index.md")

    # Generate per-project views for selected projects only.
    # When --project is used, clean only the selected project dirs.
    for proj_name, records, manifest_info in selected_results:
        proj_dir = os.path.join(REVIEW_DIR, proj_name)
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir)
        os.makedirs(proj_dir)

        # Overview
        overview = _render_overview(proj_name, records, manifest_info)
        with open(os.path.join(proj_dir, "overview.md"), "w", encoding="utf-8") as f:
            f.write(overview)
        print("Wrote: review/%s/overview.md" % proj_name)

        # Per-level views
        for level in LEVEL_MD_ORDER:
            subset = [r for r in records
                      if r.get("verification_level") == level]
            text = _render_level_view(proj_name, level, subset)
            with open(os.path.join(proj_dir, "%s.md" % level),
                      "w", encoding="utf-8") as f:
                f.write(text)
            print("Wrote: review/%s/%s.md (%d records)"
                  % (proj_name, level, len(subset)))

        # Suspicious
        suspicious = _render_suspicious_view(proj_name, records)
        with open(os.path.join(proj_dir, "suspicious.md"),
                  "w", encoding="utf-8") as f:
            f.write(suspicious)
        print("Wrote: review/%s/suspicious.md" % proj_name)

    print("\nDone.  Open review/index.md to start.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
