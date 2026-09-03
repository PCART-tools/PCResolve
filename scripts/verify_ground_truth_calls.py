#!/usr/bin/env python3
## @package scripts.verify_ground_truth_calls
#  Independent AST call coverage checker and suspicious GT selector.
#
#  1. AST coverage: extracts every ast.Call from evaluation project source files
#     and reports calls missing from GT or stale GT records.  Matching is
#     multiset: records are grouped by (file, lineno, col_offset), then
#     matched within each position by normalized expression.
#  2. Suspicious selector: flags GT records that need manual/dynamic
#     verification (transitive_method, conversion_boundary, kind mismatch,
#     owner mismatch).  Does NOT auto-change labels.
#
#  Usage:
#    python scripts/verify_ground_truth_calls.py                        # all evaluation projects, stdout only
#    python scripts/verify_ground_truth_calls.py --markdown             # write full reports
#    python scripts/verify_ground_truth_calls.py --project hfhd         # single project, stdout only
#    python scripts/verify_ground_truth_calls.py --coverage-only
#    python scripts/verify_ground_truth_calls.py --suspicious-only

import argparse
import ast
import json
import os
import re
import sys

# Reconfigure for UTF-8 to avoid UnicodeEncodeError on Windows GBK
# consoles.  Safe no-op on platforms where reconfigure is unavailable.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

GT_DIR = os.path.join(os.path.dirname(__file__), "..", "ground_truth")
PROJECTS_FILE = os.path.join(GT_DIR, "projects.json")
CALLS_DIR = os.path.join(GT_DIR, "calls")
VERIFICATION_DIR = os.path.join(GT_DIR, "verification")
FIXTURES_ROOT = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures",
                             "tested_projects")


def _norm_path(p):
    return os.path.normpath(p).replace(os.sep, "/")


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


def project_root(info):
    return os.path.normpath(os.path.join(os.path.dirname(__file__), "..",
                                         info["path"]))


def relative_file(file_path, proj_root):
    try:
        return _norm_path(os.path.relpath(file_path, proj_root))
    except ValueError:
        return _norm_path(file_path)


def extract_calls_from_file(file_path):
    """Extract all ast.Call nodes from a single Python file.

    Returns list of dicts with file, lineno, col_offset, expression.
    """
    calls = []
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            source = f.read()
    except Exception:
        return calls

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return calls

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        try:
            expr = ast.get_source_segment(source, node)
        except Exception:
            expr = ast.unparse(node) if hasattr(ast, "unparse") else "(call)"
        if expr is None:
            continue
        calls.append({
            "lineno": node.lineno,
            "col_offset": node.col_offset,
            "expression": expr.strip(),
        })

    return calls


def extract_all_calls(info):
    """Walk all .py files in a project and extract every ast.Call."""
    root = project_root(info)
    all_calls = []
    for dirpath, _, filenames in os.walk(root):
        # Skip virtual envs and hidden dirs
        if any(part.startswith(".") for part in dirpath.replace(root, "").split(os.sep) if part):
            continue
        for fn in sorted(filenames):
            if not fn.endswith(".py") and not fn.endswith(".pyi"):
                continue
            if fn.startswith("."):
                continue
            full = os.path.join(dirpath, fn)
            rel = relative_file(full, root)
            for call in extract_calls_from_file(full):
                call["file"] = rel
                all_calls.append(call)
    return all_calls


def _normalize_expr(expr):
    """Collapse whitespace in expressions for robust matching."""
    return re.sub(r"\s+", " ", expr).strip()


def _position_key(rec):
    """Match key using file + lineno + col_offset."""
    return (_norm_path(rec.get("file", "")),
            rec.get("lineno", 0),
            rec.get("col_offset", 0))


# ---------------------------------------------------------------------------
# Part 1: AST Call Coverage (multiset matching)
# ---------------------------------------------------------------------------

def check_coverage(proj_name, info):
    """Compare AST calls vs GT records; return coverage report dict.

    Groups records and AST calls by (file, lineno, col_offset), then
    matches within each position by normalized expression.  When
    expression matching is exhausted and the per-position counts are
    equal, remaining records are paired by source order (handles quote
    style differences).

    A GT record is *stale* when it cannot be matched to any AST call
    at its position.  An AST call is *missing* when it cannot be
    matched to any GT record at its position.
    """
    gt_records = load_gt(proj_name)
    ast_calls = extract_all_calls(info)

    # Multiset grouping: pos -> list[record]
    gt_by_pos = {}
    for r in gt_records:
        gt_by_pos.setdefault(_position_key(r), []).append(r)

    ast_by_pos = {}
    for c in ast_calls:
        ast_by_pos.setdefault(_position_key(c), []).append(c)

    all_positions = set(gt_by_pos.keys()) | set(ast_by_pos.keys())

    missing_from_gt = []
    stale_in_gt = []
    expr_mismatches = []

    for pos in sorted(all_positions):
        gt_list = gt_by_pos.get(pos, [])
        ast_list = ast_by_pos.get(pos, [])

        if not gt_list:
            # AST calls with no GT record at this position
            missing_from_gt.extend(ast_list)
            continue
        if not ast_list:
            # GT records with no AST call at this position
            stale_in_gt.extend(gt_list)
            continue

        # Within-position matching by normalized expression
        # Build pool of AST calls keyed by normalized expression
        ast_pool = {}
        for ac in ast_list:
            ne = _normalize_expr(ac["expression"])
            ast_pool.setdefault(ne, []).append(ac)

        gt_unmatched = []
        for gr in gt_list:
            ne = _normalize_expr(gr.get("expression", ""))
            if ne in ast_pool and ast_pool[ne]:
                ast_pool[ne].pop(0)
            else:
                gt_unmatched.append(gr)

        # Collect remaining AST calls
        ast_unmatched = []
        for remaining in ast_pool.values():
            ast_unmatched.extend(remaining)

        # Fallback: equal counts -> pair by order (covers quote diffs)
        if len(gt_unmatched) == len(ast_unmatched) and gt_unmatched:
            for gr, ac in zip(gt_unmatched, ast_unmatched):
                if _normalize_expr(gr.get("expression", "")) != _normalize_expr(ac["expression"]):
                    expr_mismatches.append({
                        "file": ac["file"],
                        "lineno": ac["lineno"],
                        "col_offset": ac["col_offset"],
                        "ast_expression": ac["expression"],
                        "gt_expression": gr.get("expression", ""),
                    })
            gt_unmatched = []
            ast_unmatched = []

        missing_from_gt.extend(ast_unmatched)
        stale_in_gt.extend(gt_unmatched)

    covered_gt = len(gt_records) - len(stale_in_gt)
    covered_ast = len(ast_calls) - len(missing_from_gt)

    return {
        "project": proj_name,
        "ast_call_count": len(ast_calls),
        "gt_record_count": len(gt_records),
        "covered_gt": covered_gt,
        "covered_ast": covered_ast,
        "missing_from_gt": missing_from_gt,
        "missing_from_gt_count": len(missing_from_gt),
        "stale_in_gt": stale_in_gt,
        "stale_in_gt_count": len(stale_in_gt),
        "expr_mismatches": expr_mismatches,
        "expr_mismatch_count": len(expr_mismatches),
    }


# ---------------------------------------------------------------------------
# Part 2: Suspicious GT Selector
# ---------------------------------------------------------------------------

def _is_transitive_method(cat):
    if not cat:
        return False
    return "transitive_method" in cat.lower()


def _is_conversion_boundary(cat):
    if not cat:
        return False
    return "conversion_boundary" in cat.lower()


def select_suspicious(proj_name):
    """Identify GT records that need manual/dynamic verification.

    Selectors:
      - transitive_method category
      - conversion_boundary category
      - expected_kind == "library" but pcresolve_kind != "library"
      - pcresolve_top_library != expected_top_library
    """
    records = load_gt(proj_name)
    suspicious = []
    reasons = {}

    for r in records:
        flags = []

        cat = r.get("category", "") or ""
        if _is_transitive_method(cat):
            flags.append("transitive_method")
        if _is_conversion_boundary(cat):
            flags.append("conversion_boundary")

        ek = r.get("expected_kind", "")
        etl = r.get("expected_top_library", "")
        pck = r.get("pcresolve_kind", "")
        pctl = r.get("pcresolve_top_library", "")

        # For manual_gt records, pcresolve fields are empty
        if r.get("source") == "manual_gt":
            if ek == "library":
                flags.append("manual_gt_library_call_missed_by_pcresolve")

        if ek == "library" and pck and pck != "library":
            flags.append("expected_library_but_pcresolve_not_library")
        if pctl and etl and pctl != etl:
            flags.append("pcresolve_top_library_mismatch_expected")

        if flags:
            r_copy = dict(r)
            r_copy["_flags"] = flags
            suspicious.append(r_copy)
            for f in flags:
                reasons[f] = reasons.get(f, 0) + 1

    return {
        "project": proj_name,
        "total_records": len(records),
        "suspicious_count": len(suspicious),
        "reason_counts": reasons,
        "suspicious": suspicious,
    }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_coverage_report(results, out):
    out.append("=" * 72)
    out.append("AST CALL COVERAGE CHECK")
    out.append("=" * 72)
    out.append("")
    out.append("Compares independent ast.Call extraction against GT JSONL records.")
    out.append("Matching: multiset by (file, lineno, col_offset) then normalized")
    out.append("expression within each position.  Fallback order-pairing handles")
    out.append("quote-style differences at duplicate positions.")
    out.append("")

    total_ast = 0
    total_gt = 0
    total_missing = 0
    total_stale = 0

    for r in results:
        total_ast += r["ast_call_count"]
        total_gt += r["gt_record_count"]
        total_missing += r["missing_from_gt_count"]
        total_stale += r["stale_in_gt_count"]

    total_expr_mismatch = sum(r.get("expr_mismatch_count", 0) for r in results)

    out.append("%-12s %8s %8s %8s %8s %8s" % (
        "Project", "AST_Call", "GT_Recs", "Missing", "Stale",
        "ExprDiff"))
    out.append("-" * 72)
    for r in results:
        out.append("%-12s %8d %8d %8d %8d %8d" % (
            r["project"], r["ast_call_count"], r["gt_record_count"],
            r["missing_from_gt_count"],
            r["stale_in_gt_count"], r.get("expr_mismatch_count", 0)))

    out.append("-" * 72)
    out.append("%-12s %8d %8d %8d %8d %8d" % (
        "TOTAL", total_ast, total_gt, total_missing, total_stale,
        total_expr_mismatch))
    out.append("")

    # Detail: missing from GT
    if total_missing > 0:
        out.append("-" * 72)
        out.append("CALLS MISSING FROM GT (no matching GT record at position)")
        out.append("-" * 72)
        for r in results:
            if r["missing_from_gt"]:
                out.append("")
                out.append("[%s] %d calls not covered:" % (r["project"], r["missing_from_gt_count"]))
                for c in sorted(r["missing_from_gt"],
                                key=lambda x: (x["file"], x["lineno"], x["col_offset"])):
                    out.append("  %s:%d:%d  %s" % (
                        c["file"], c["lineno"], c["col_offset"],
                        c["expression"][:120]))
        out.append("")

    # Detail: stale GT
    if total_stale > 0:
        out.append("-" * 72)
        out.append("STALE GT RECORDS (no matching ast.Call at position)")
        out.append("-" * 72)
        for r in results:
            if r["stale_in_gt"]:
                out.append("")
                out.append("[%s] %d stale records:" % (r["project"], r["stale_in_gt_count"]))
                for rec in sorted(r["stale_in_gt"],
                                  key=lambda x: (x.get("file", ""), x.get("lineno", 0))):
                    out.append("  %s:%d:%d  %s  (source=%s)" % (
                        rec.get("file", ""), rec.get("lineno", 0),
                        rec.get("col_offset", 0),
                        rec.get("expression", "")[:100],
                        rec.get("source", "?")))
        out.append("")

    # Detail: expression mismatches on position+order-matched records
    total_expr_mismatch = sum(r.get("expr_mismatch_count", 0) for r in results)
    if total_expr_mismatch > 0:
        out.append("-" * 72)
        out.append("EXPRESSION MISMATCHES (matched by position+order, expression differs)")
        out.append("-" * 72)
        out.append("Position-matched by fallback order-pairing at duplicate positions.")
        out.append("Typically caused by quote style differences or manual annotation")
        out.append("typos.  Review for correctness.")
        out.append("")
        for r in results:
            if r.get("expr_mismatches"):
                out.append("[%s] %d expression mismatches:" % (
                    r["project"], r["expr_mismatch_count"]))
                for em in sorted(r["expr_mismatches"],
                                 key=lambda x: (x["file"], x["lineno"], x["col_offset"])):
                    out.append("  %s:%d:%d" % (em["file"], em["lineno"], em["col_offset"]))
                    out.append("    AST: %s" % em["ast_expression"][:120])
                    out.append("    GT:  %s" % em["gt_expression"][:120])
                    out.append("")
        out.append("")

    out.append("Coverage summary: %d/%d AST calls covered by GT (%.1f%%)" % (
        total_ast - total_missing, total_ast,
        100 * (total_ast - total_missing) / total_ast if total_ast > 0 else 0))
    out.append("")


def print_suspicious_report(results, out):
    out.append("=" * 72)
    out.append("SUSPICIOUS GT SELECTOR")
    out.append("=" * 72)
    out.append("")
    out.append("Flags GT records that need manual/dynamic verification.")
    out.append("Does NOT auto-change labels.  Review each flagged record.")
    out.append("")
    out.append("Selectors applied:")
    out.append("  transitive_method    - category contains 'transitive_method'")
    out.append("  conversion_boundary  - category contains 'conversion_boundary'")
    out.append("  expected_library_but_pcresolve_not_library")
    out.append("                        - expected_kind=library but pcresolve_kind!=library")
    out.append("  pcresolve_top_library_mismatch_expected")
    out.append("                        - pcresolve_top_library != expected_top_library")
    out.append("  manual_gt_library_call_missed_by_pcresolve")
    out.append("                        - manual_gt entries with expected_kind=library")
    out.append("")

    total_suspicious = 0
    for r in results:
        total_suspicious += r["suspicious_count"]

    out.append("%-12s %8s %8s  %s" % ("Project", "Records", "Suspicious", "Reason Breakdown"))
    out.append("-" * 72)
    for r in results:
        breakdown = ", ".join("%s=%d" % (k, v)
                              for k, v in sorted(r["reason_counts"].items()))
        out.append("%-12s %8d %8d  %s" % (
            r["project"], r["total_records"], r["suspicious_count"],
            breakdown))
    out.append("-" * 72)
    out.append("%-12s %8s %8d" % ("TOTAL", "", total_suspicious))
    out.append("")

    # Detail per project
    for r in results:
        if not r["suspicious"]:
            continue
        out.append("-" * 72)
        out.append("[%s] %d suspicious records:" % (r["project"], r["suspicious_count"]))
        out.append("-" * 72)

        # Group by flag
        by_flag = {}
        for rec in r["suspicious"]:
            for flag in rec["_flags"]:
                by_flag.setdefault(flag, []).append(rec)

        for flag in sorted(by_flag):
            recs = by_flag[flag]
            out.append("")
            out.append("  --- %s (%d records) ---" % (flag, len(recs)))
            for rec in sorted(recs, key=lambda x: (x.get("file", ""), x.get("lineno", 0))):
                ek = rec.get("expected_kind", "")
                etl = rec.get("expected_top_library", "")
                pck = rec.get("pcresolve_kind", "")
                pctl = rec.get("pcresolve_top_library", "")
                status = rec.get("status", "")
                cat = rec.get("category", "")
                notes = rec.get("notes", "")
                out.append("    %s:%d:%d  %s" % (
                    rec.get("file", ""), rec.get("lineno", 0),
                    rec.get("col_offset", 0),
                    rec.get("expression", "")[:100]))
                out.append("      expected: kind=%s top=%s  |  pcresolve: kind=%s top=%s"
                           % (ek, etl, pck, pctl))
                out.append("      status=%s category=%s source=%s" % (
                    status, cat, rec.get("source", "")))
                if notes:
                    out.append("      notes: %s" % notes[:200])
        out.append("")


def _is_full_pilot_run(pilot_names, manifest):
    """Check whether the selected projects cover the full evaluation corpus."""
    all_pilots = set(n for n, info in manifest.items()
                     if info.get("tier") == "pilot")
    return set(pilot_names) == all_pilots


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def _build_parser():
    parser = argparse.ArgumentParser(
        description="AST call coverage checker and suspicious GT selector")
    parser.add_argument("--project", action="append", default=[],
                        metavar="NAME",
                        help="Only check this project (repeatable)")
    parser.add_argument("--coverage-only", action="store_true",
                        help="Only run AST call coverage check")
    parser.add_argument("--suspicious-only", action="store_true",
                        help="Only run suspicious GT selector")
    parser.add_argument("--write", action="store_true",
                        help="Write JSON/md output files (canonical names)")
    parser.add_argument("--markdown", action="store_true",
                        help="Alias for --write (also writes .md report)")
    return parser


def _validate_projects(selected, manifest):
    """Validate selected project names exist in manifest.  Returns list of
    unknown names, or empty list if all valid."""
    all_names = set(manifest.keys())
    return [n for n in selected if n not in all_names]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = _build_parser()
    ns = parser.parse_args(argv)

    if ns.coverage_only and ns.suspicious_only:
        parser.error("--coverage-only and --suspicious-only "
                     "are mutually exclusive")

    manifest = load_manifest()

    # Validate project names
    unknown = _validate_projects(ns.project, manifest)
    if unknown:
        for name in unknown:
            print("ERROR: unknown project '%s'" % name, file=sys.stderr)
        return 1

    do_coverage = not ns.suspicious_only
    do_suspicious = not ns.coverage_only
    write_files = ns.write or ns.markdown

    os.makedirs(VERIFICATION_DIR, exist_ok=True)

    pilot_names = [n for n, info in manifest.items()
                   if info.get("tier") == "pilot"]
    if ns.project:
        pilot_names = [n for n in pilot_names if n in ns.project]

    if not pilot_names:
        print("ERROR: no evaluation projects matched", file=sys.stderr)
        return 1

    is_full = _is_full_pilot_run(pilot_names, manifest)

    coverage_results = []
    suspicious_results = []

    for name in pilot_names:
        info = manifest[name]
        root = project_root(info)
        if not os.path.isdir(root):
            print("SKIP %s: path not found (%s)" % (name, root))
            continue

        if do_coverage:
            cov = check_coverage(name, info)
            coverage_results.append(cov)

        if do_suspicious:
            sus = select_suspicious(name)
            suspicious_results.append(sus)

    # Collect output lines
    out = []
    out.append("PCResolve 1.0.5 Ground Truth Verification Report")
    out.append("Generated by: scripts/verify_ground_truth_calls.py")
    out.append("Projects: %s" % ", ".join(pilot_names))
    out.append("")

    if do_coverage:
        print_coverage_report(coverage_results, out)

    if do_suspicious:
        print_suspicious_report(suspicious_results, out)

    if total_stale_found := sum(r["stale_in_gt_count"] for r in coverage_results):
        out.append("")
        out.append("*** RECOMMENDATION: Review %d stale GT records. They may need"
                   % total_stale_found)
        out.append("    updating or removal if the source code has changed.")

    if total_missing_found := sum(r["missing_from_gt_count"] for r in coverage_results):
        out.append("")
        out.append("*** RECOMMENDATION: Review %d AST calls missing from GT. Add manual_gt"
                   % total_missing_found)
        out.append("    entries for any calls that should be in the evaluation.")

    # Print to stdout
    report_text = "\n".join(out)
    print(report_text)

    # Decide whether to write canonical files
    if write_files and not is_full:
        print("")
        print("NOTE: --project filter active but --write specified.")
        print("      Writing canonical filenames with partial project set.")
    elif not write_files and not is_full:
        print("")
        print("NOTE: --project filter active. Use --write to persist output files.")
        print("      Without --write, only stdout is produced.")
        return 0
    elif not write_files:
        return 0

    # Write to files
    md_path = os.path.join(VERIFICATION_DIR, "verification_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print("\nReport written to: %s" % md_path)

    if do_coverage:
        cov_json = []
        for r in coverage_results:
            cov_json.append({
                "project": r["project"],
                "ast_call_count": r["ast_call_count"],
                "gt_record_count": r["gt_record_count"],
                "covered_gt": r["covered_gt"],
                "covered_ast": r["covered_ast"],
                "missing_from_gt_count": r["missing_from_gt_count"],
                "stale_in_gt_count": r["stale_in_gt_count"],
                "expr_mismatch_count": r.get("expr_mismatch_count", 0),
                "missing_from_gt": [
                    {"file": c["file"], "lineno": c["lineno"],
                     "col_offset": c["col_offset"],
                     "expression": c["expression"]}
                    for c in r["missing_from_gt"]
                ],
                "stale_in_gt": [
                    {"file": rec.get("file", ""),
                     "lineno": rec.get("lineno", 0),
                     "col_offset": rec.get("col_offset", 0),
                     "expression": rec.get("expression", ""),
                     "source": rec.get("source", ""),
                     "status": rec.get("status", "")}
                    for rec in r["stale_in_gt"]
                ],
                "expr_mismatches": r.get("expr_mismatches", []),
            })
        cov_json_path = os.path.join(VERIFICATION_DIR, "coverage_check.json")
        with open(cov_json_path, "w", encoding="utf-8") as f:
            json.dump(cov_json, f, indent=2, ensure_ascii=False)
        print("Coverage JSON written to: %s" % cov_json_path)

    if do_suspicious:
        sus_json = []
        for r in suspicious_results:
            sus_json.append({
                "project": r["project"],
                "total_records": r["total_records"],
                "suspicious_count": r["suspicious_count"],
                "reason_counts": r["reason_counts"],
                "suspicious": [
                    {k: v for k, v in rec.items() if not k.startswith("_")}
                    for rec in r["suspicious"]
                ],
            })
        sus_json_path = os.path.join(VERIFICATION_DIR, "suspicious_selector.json")
        with open(sus_json_path, "w", encoding="utf-8") as f:
            json.dump(sus_json, f, indent=2, ensure_ascii=False)
        print("Suspicious JSON written to: %s" % sus_json_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
