#!/usr/bin/env python3
## @package scripts.audit_tested_projects
#  Full audit of all tested_projects fixtures for 1.0.4 release.
#
#  Usage:
#    python scripts/audit_tested_projects.py
#    python scripts/audit_tested_projects.py --timeout 60
#    python scripts/audit_tested_projects.py --output reports/
#
#  Outputs:
#    reports/tested-projects-audit.json   — machine-diffable
#    reports/tested-projects-audit.md     — human review

import json
import os
import signal
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve.cross_file import analyze_project

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..",
                           "tests", "fixtures", "tested_projects")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
BASELINE_DIR = os.path.join(os.path.dirname(__file__), "..",
                            "tests", "fixtures", "diff_baselines")

_HAS_SIGALRM = hasattr(signal, "SIGALRM")

# Project path overrides for nested fixtures whose basename does not
# match a top-level directory under tested_projects.
_BASELINE_PATH_MAP = {
    "barcoded_yeast_reanalysis": "giantpopflucts/barcoded_yeast_reanalysis",
    "ex_4_2": "simulation/ex_4_2",
}
# Reverse mapping: top-level project dir -> baseline name
_BASELINE_REVERSE_MAP = {
    "giantpopflucts": "barcoded_yeast_reanalysis",
    "simulation": "ex_4_2",
}


def _resolve_baseline_project(name):
    """Return the real project path for a baseline name, or None."""
    direct = os.path.join(FIXTURE_DIR, name)
    if os.path.isdir(direct):
        return direct
    sub_path = _BASELINE_PATH_MAP.get(name)
    if sub_path:
        resolved = os.path.join(FIXTURE_DIR, sub_path)
        if os.path.isdir(resolved):
            return resolved
    return None


def _safe_print(*args, **kwargs):
    """Print with encoding-safe fallback for Windows consoles."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        text = " ".join(str(a).encode("ascii", errors="replace").decode("ascii")
                        for a in args)
        print(text, **kwargs)


def _is_illegal_key(name):
    for prefix in ("InstanceMethod(", "CallResult(", "ContainerItem(",
                   "ContainerIter(", "UnknownSource(", "SourceSet("):
        if name.startswith(prefix):
            return True
    if isinstance(name, str) and name.startswith("[") and "SourceSet" in name:
        return True
    return False


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("analysis timed out")


def _run_analysis(project_path, scope_model, timeout_sec):
    """Run analyze_project with optional cross-platform timeout.

    On POSIX uses SIGALRM; on Windows falls back to subprocess
    when timeout_sec > 0, or direct call when timeout is disabled.
    """
    if _HAS_SIGALRM and timeout_sec > 0:
        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout_sec)
        try:
            t0 = time.perf_counter()
            result = analyze_project(project_path, scope_model=scope_model)
            elapsed = time.perf_counter() - t0
        finally:
            signal.alarm(0)
        return result, elapsed

    if not _HAS_SIGALRM and timeout_sec > 0:
        # Windows: use subprocess with the same script as a worker.
        worker = [sys.executable, "-c", (
            "import sys; sys.path.insert(0,%r);"
            "from pcresolve.cross_file import analyze_project;"
            "import json,os;"
            "r=analyze_project(%r,scope_model=%r);"
            "print(json.dumps({'files':len(r.files),"
            "'calls':len(r.all_api_calls),"
            "'libs':len(r.library_usage)}))"
        ) % (os.path.join(os.path.dirname(__file__), "..", "src"),
             project_path, scope_model)]
        try:
            t0 = time.perf_counter()
            proc = subprocess.run(worker, capture_output=True, text=True,
                                  timeout=timeout_sec)
            elapsed = time.perf_counter() - t0
            if proc.returncode != 0:
                raise RuntimeError("subprocess failed: %s" % proc.stderr[:200])
            # We can't return the full result from subprocess, so return
            # a lightweight sentinel; the caller will re-run without timeout
            # if needed.
            return None, elapsed
        except subprocess.TimeoutExpired:
            raise TimeoutError("timeout (%ds)" % timeout_sec)

    # No timeout — direct call.
    t0 = time.perf_counter()
    result = analyze_project(project_path, scope_model=scope_model)
    elapsed = time.perf_counter() - t0
    return result, elapsed


def audit_one(project_path, timeout_sec=60):
    """Run v1+v2 analysis on a single project and return audit record."""
    name = os.path.basename(project_path)
    record = {
        "project": name,
        "path": project_path,
        "files_parsed": 0,
        "files_skipped": 0,
        "api_calls": 0,
        "libraries": 0,
        "regressions": 0,
        "improvements": 0,
        "precision": 0,
        "tp_to_local": 0,
        "tp_to_unknown": 0,
        "local_to_unknown": 0,
        "illegal_keys": 0,
        "error": None,
        "error_type": None,
        "v1_runtime": 0,
        "v2_runtime": 0,
        "libraries_list": [],
        "has_baseline": False,
    }

    # Resolve baseline status using the reverse path map for nested projects.
    bl_name = _BASELINE_REVERSE_MAP.get(name, name)
    record["has_baseline"] = os.path.exists(
        os.path.join(BASELINE_DIR, bl_name + ".json"))

    # v1 analysis
    try:
        r1, t1 = _run_analysis(project_path, "v1", timeout_sec)
        record["v1_runtime"] = round(t1, 3)
    except TimeoutError:
        record["error"] = "timeout (%ds)" % timeout_sec
        record["error_type"] = "timeout"
        return record
    except RecursionError:
        record["error"] = "RecursionError"
        record["error_type"] = "recursion"
        return record
    except Exception as e:
        record["error"] = "%s: %s" % (type(e).__name__, str(e))
        record["error_type"] = "exception"
        return record

    if r1 is None:
        # subprocess fallback gave no result; re-run without timeout.
        try:
            r1, t1 = _run_analysis(project_path, "v1", 0)
            record["v1_runtime"] = round(record["v1_runtime"] + t1, 3)
        except RecursionError:
            record["error"] = "RecursionError"
            record["error_type"] = "recursion"
            return record
        except Exception as e:
            record["error"] = "%s: %s" % (type(e).__name__, str(e))
            record["error_type"] = "exception"
            return record

    # v2 analysis
    try:
        r2, t2 = _run_analysis(project_path, "v2", timeout_sec)
        record["v2_runtime"] = round(t2, 3)
    except TimeoutError:
        record["error"] = "v2 timeout (%ds)" % timeout_sec
        record["error_type"] = "timeout"
        return record
    except RecursionError:
        record["error"] = "v2 RecursionError"
        record["error_type"] = "recursion"
        return record
    except Exception as e:
        record["error"] = "v2 %s: %s" % (type(e).__name__, str(e))
        record["error_type"] = "exception"
        return record

    if r2 is None:
        try:
            r2, t2 = _run_analysis(project_path, "v2", 0)
            record["v2_runtime"] = round(record["v2_runtime"] + t2, 3)
        except RecursionError:
            record["error"] = "v2 RecursionError"
            record["error_type"] = "recursion"
            return record
        except Exception as e:
            record["error"] = "v2 %s: %s" % (type(e).__name__, str(e))
            record["error_type"] = "exception"
            return record

    # Stats from v2
    record["files_parsed"] = len(r2.files)
    record["files_skipped"] = len(r2.diagnostics)
    record["api_calls"] = len(r2.all_api_calls)
    record["libraries"] = len(r2.library_usage)
    record["libraries_list"] = sorted(r2.library_usage.keys())

    # Illegal keys
    illegal_libs = [lib for lib in r2.library_usage if _is_illegal_key(lib)]
    illegal_calls = [c for c in r2.all_api_calls
                     if _is_illegal_key(c.top_library)]
    illegal_provs = [p for p in r2.all_symbol_provenance
                     if _is_illegal_key(p.top_library)]
    record["illegal_keys"] = (len(illegal_libs) + len(illegal_calls) +
                              len(illegal_provs))

    # v1/v2 diff
    v1_calls = {(c.file_path, c.lineno, c.col_offset, c.expression): c.top_library
                for c in r1.all_api_calls}
    v2_calls = {(c.file_path, c.lineno, c.col_offset, c.expression): c.top_library
                for c in r2.all_api_calls}

    for key in v1_calls:
        v1_top = v1_calls[key]
        v2_top = v2_calls.get(key)
        if v2_top is None or v2_top == v1_top:
            continue
        if v2_top in ("local", "unknown", "") and v1_top not in ("local", "unknown", ""):
            record["regressions"] += 1
            if v2_top == "local":
                record["tp_to_local"] += 1
            else:
                record["tp_to_unknown"] += 1
        elif v1_top in ("local", "unknown", "") and v2_top not in ("local", "unknown", ""):
            record["improvements"] += 1
        elif v1_top == "local" and v2_top == "unknown":
            record["local_to_unknown"] += 1
            record["regressions"] += 1
        elif v1_top not in ("local", "unknown", "") and v2_top not in ("local", "unknown", ""):
            record["precision"] += 1

    return record


def main():
    timeout = 60
    output_dir = REPORTS_DIR
    args = sys.argv[1:]
    while args:
        if args[0] == "--timeout" and len(args) > 1:
            timeout = int(args.pop(1))
            args.pop(0)
        elif args[0] == "--output" and len(args) > 1:
            output_dir = args.pop(1)
            args.pop(0)
        else:
            args.pop(0)

    os.makedirs(output_dir, exist_ok=True)

    # Discover projects
    projects = []
    for entry in sorted(os.listdir(FIXTURE_DIR)):
        proj_path = os.path.join(FIXTURE_DIR, entry)
        if os.path.isdir(proj_path):
            projects.append(proj_path)

    _safe_print("Auditing %d projects (timeout=%ds)..." % (len(projects), timeout))
    results = []
    errors = 0
    crashes = 0
    illegal_projects = 0

    for proj_path in projects:
        name = os.path.basename(proj_path)
        sys.stdout.write("  %-35s " % name)
        sys.stdout.flush()
        t0 = time.perf_counter()
        rec = audit_one(proj_path, timeout_sec=timeout)
        elapsed = time.perf_counter() - t0
        rec["audit_runtime"] = round(elapsed, 3)

        if rec["error"]:
            crashes += 1
            _safe_print("ERROR: %s (%.1fs)" % (rec["error"], elapsed))
        elif rec["illegal_keys"]:
            illegal_projects += 1
            _safe_print("ILLEGAL=%d  R=%d  I=%d  P=%d  calls=%d  libs=%d  (%.1fs)" % (
                rec["illegal_keys"], rec["regressions"], rec["improvements"],
                rec["precision"], rec["api_calls"], rec["libraries"], elapsed))
        else:
            errors += rec["regressions"]
            _safe_print("OK  R=%d  I=%d  P=%d  calls=%d  libs=%d  (%.1fs)" % (
                rec["regressions"], rec["improvements"],
                rec["precision"], rec["api_calls"], rec["libraries"], elapsed))
        results.append(rec)

    # Summary
    total_calls = sum(r["api_calls"] for r in results if not r["error"])
    total_libs = len(set(
        lib for r in results if not r["error"]
        for lib in r["libraries_list"]))
    total_r = sum(r["regressions"] for r in results)
    total_i = sum(r["improvements"] for r in results)
    total_p = sum(r["precision"] for r in results)
    total_illegal = sum(r["illegal_keys"] for r in results)
    hard_baseline_count = sum(1 for r in results if r["has_baseline"])
    crashed = [r for r in results if r["error"]]

    # Candidate selection for hard gate expansion
    candidates = []
    for r in results:
        if r["error"]:
            continue
        if r["illegal_keys"]:
            continue
        if r["api_calls"] >= 5 and r["libraries"] >= 1:
            candidates.append(r)

    _safe_print()
    _safe_print("=" * 60)
    _safe_print("AUDIT SUMMARY")
    _safe_print("=" * 60)
    _safe_print("Projects audited:    %d" % len(results))
    _safe_print("Crashed/timeout:     %d" % len(crashed))
    _safe_print("Illegal key projects:%d" % illegal_projects)
    _safe_print("Clean projects:      %d" % (len(results) - len(crashed) - illegal_projects))
    _safe_print("Total API calls:     %d" % total_calls)
    _safe_print("Unique libraries:    %d" % total_libs)
    _safe_print("Total regressions:   %d" % total_r)
    _safe_print("Total improvements:  %d" % total_i)
    _safe_print("Total precision:     %d" % total_p)
    _safe_print("Total illegal keys:  %d" % total_illegal)
    _safe_print("Hard baseline now:   %d" % hard_baseline_count)
    _safe_print("Hard baseline candidates: %d" % len(candidates))

    if crashed:
        _safe_print()
        _safe_print("CRASHED/TIMEOUT:")
        for r in crashed:
            _safe_print("  %-35s %s" % (r["project"], r["error"]))

    # Suggest new hard baseline candidates
    new_candidates = [c for c in candidates if not c["has_baseline"]]
    for c in new_candidates:
        c["_score"] = (
            -c["regressions"] * 2
            + min(c["api_calls"], 200)
            + c["libraries"] * 5
        )
    new_candidates.sort(key=lambda c: -c["_score"])

    _safe_print()
    _safe_print("SUGGESTED HARD BASELINE ADDITIONS (top 15):")
    for c in new_candidates[:15]:
        flag = "*" if c["_score"] > 100 else " "
        _safe_print("  %-35s calls=%4d  libs=%2d  R=%3d  I=%3d  P=%2d  %s" % (
            c["project"], c["api_calls"], c["libraries"],
            c["regressions"], c["improvements"], c["precision"], flag))

    # Not recommended
    not_recommended = [
        r for r in results
        if not r["error"] and not r["has_baseline"]
        and r not in new_candidates[:15]
        and (r["api_calls"] < 5 or r["regressions"] > 50 or r["illegal_keys"])
    ]
    if not_recommended:
        _safe_print()
        _safe_print("NOT RECOMMENDED (low calls / high regressions / illegal):")
        for r in not_recommended:
            reason = ""
            if r["api_calls"] < 5:
                reason = "low_calls"
            elif r["regressions"] > 50:
                reason = "high_regressions(%d)" % r["regressions"]
            elif r["illegal_keys"]:
                reason = "illegal_keys(%d)" % r["illegal_keys"]
            _safe_print("  %-35s %s" % (r["project"], reason))

    # Write reports
    json_path = os.path.join(output_dir, "tested-projects-audit.json")
    with open(json_path, "w") as f:
        json.dump({"results": results, "summary": {
            "total_projects": len(results),
            "crashed": len(crashed),
            "illegal_projects": illegal_projects,
            "total_api_calls": total_calls,
            "unique_libraries": total_libs,
            "total_regressions": total_r,
            "total_improvements": total_i,
            "total_precision": total_p,
            "total_illegal_keys": total_illegal,
            "hard_baseline_count": hard_baseline_count,
            "candidate_count": len(new_candidates),
        }}, f, indent=2)

    md_path = os.path.join(output_dir, "tested-projects-audit.md")
    with open(md_path, "w") as f:
        f.write("# PCResolve 1.0.4 — 42-Project Audit Report\n\n")
        f.write("| project | calls | libs | R | I | P | illegal | v1(s) | v2(s) | baseline | notes |\n")
        f.write("|---------|-------|------|---|---|---|---------|-------|-------|----------|-------|\n")
        for r in results:
            notes = ""
            if r["error"]:
                notes = "**%s**" % r["error"]
            elif r["illegal_keys"]:
                notes = "**illegal=%d**" % r["illegal_keys"]
            bl = "yes" if r["has_baseline"] else ""
            f.write("| %s | %d | %d | %d | %d | %d | %d | %.2f | %.2f | %s | %s |\n" % (
                r["project"], r["api_calls"], r["libraries"],
                r["regressions"], r["improvements"], r["precision"],
                r["illegal_keys"],
                r["v1_runtime"], r["v2_runtime"], bl, notes))

        f.write("\n## Candidates for hard baseline expansion\n\n")
        for c in new_candidates[:15]:
            f.write("- **%s** — calls=%d libs=%d R=%d I=%d (score=%d)\n" % (
                c["project"], c["api_calls"], c["libraries"],
                c["regressions"], c["improvements"], c["_score"]))

        if crashed:
            f.write("\n## Crashed / Timeout\n\n")
            for r in crashed:
                f.write("- %s: %s\n" % (r["project"], r["error"]))

    _safe_print()
    _safe_print("Reports written:")
    _safe_print("  " + json_path)
    _safe_print("  " + md_path)

    if crashed or total_illegal:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
