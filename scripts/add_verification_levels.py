#!/usr/bin/env python3
## @package scripts.add_verification_levels
#  Add verification_level and verification_notes to GT JSONL records,
#  then check lock readiness.
#
#  Classification rules (auto-applied, no manual editing):
#
#    static_obvious   — direct import, builtin, local callable, decorator expr
#    static_context   — needs code context reading to confirm
#    dynamic_probe    — confirmed by minimal dynamic probe
#    manual_reasoned  — needs human reasoning beyond current probes
#    unsupported      — beyond 1.0.5 static analysis scope
#
#  Usage:
#    python scripts/add_verification_levels.py           # classify all pilots
#    python scripts/add_verification_levels.py --check   # only check lock readiness
#    python scripts/add_verification_levels.py --dry-run  # classify but don't write

import argparse
import json
import os
import sys

GT_DIR = os.path.join(os.path.dirname(__file__), "..", "ground_truth")
CALLS_DIR = os.path.join(GT_DIR, "calls")
VERIFICATION_DIR = os.path.join(GT_DIR, "verification")
PROJECTS_FILE = os.path.join(GT_DIR, "projects.json")

# ---------------------------------------------------------------------------
# Classification rules
# ---------------------------------------------------------------------------


def _classify(rec):
    """Return (verification_level, verification_notes) for a GT record."""
    cat = rec.get("category", "") or ""
    expr = rec.get("expression", "") or ""
    notes = rec.get("notes", "") or ""

    # -- static_obvious: mechanistically verifiable ------------------------
    if cat == "direct_import":
        return ("static_obvious", "direct import-backed API call")

    if cat == "decorator_expression":
        return ("static_obvious", "decorator expression is import-backed usage")

    if cat == "builtin":
        return ("static_obvious", "Python builtin function call")

    if cat == "local_call":
        return ("static_obvious", "project-local function/method call")

    # -- conversion_boundary: confirmed by dynamic probes ------------------
    if cat == "conversion_boundary":
        if "to_numpy" in expr or "to_numpy" in notes:
            return ("dynamic_probe",
                    "probe confirms .to_numpy() is pandas API, "
                    "returned ndarray is numpy")
        return ("dynamic_probe",
                "conversion boundary confirmed by to_numpy/values probe")

    # -- decorated_callable_receiver ---------------------------------------
    if cat == "decorated_callable_receiver":
        return ("static_context",
                "decorated local callable; primary identity is local, "
                "decorator evidence in decorated_by")

    # -- builtin_method_local_receiver -------------------------------------
    if cat == "builtin_method_local_receiver":
        if "append" in expr or "extend" in expr or "index" in expr:
            return ("static_context",
                    "builtin list method on local container; "
                    "receiver is local list literal or variable")
        if ".get(" in expr:
            return ("static_context",
                    "builtin dict.get on local container; "
                    "receiver is local dict literal")
        return ("static_context",
                "builtin method on local receiver")

    # -- mapping_protocol_method -------------------------------------------
    if cat == "mapping_protocol_method":
        return ("static_context",
                "mapping protocol receiver; GT labels python per "
                "protocol convention, surrounding context uses "
                "in/subscript/.get on request.json payload")

    # -- transitive_method: depends on receiver ----------------------------
    if cat == "transitive_method":
        return _classify_transitive(rec)

    # -- Fallback ---------------------------------------------------------
    return ("manual_reasoned", "no auto-classification rule matched")


def _classify_transitive(rec):
    """Classify transitive_method records based on expression patterns."""
    expr = rec.get("expression", "") or ""
    etl = rec.get("expected_top_library", "")
    pctl = rec.get("pcresolve_top_library", "")

    # --- Dynamic probe confirmed patterns ---------------------------------
    # np.log(pd.Series).diff() -> pandas receiver
    if "np.log" in expr and ".diff()" in expr:
        return ("dynamic_probe",
                "probe confirms np.log(pd.Series) returns pd.Series, "
                ".diff() is pandas method; PCResolve says numpy (wrong_owner)")

    # .diff() on pandas Series from other paths
    if ".diff()" in expr and etl == "pandas":
        return ("static_context",
                ".diff() on pandas Series; pandas method on pandas object")

    # .mean() on pandas Series/ndarray result
    if ".mean()" in expr:
        if etl == "numpy" and pctl in ("scipy", "numpy"):
            return ("dynamic_probe",
                    "probe confirms ndarray.mean() is numpy method")
        if etl == "pandas":
            return ("static_context",
                    ".mean() on pandas Series")

    # cdist return -> .argmin() on ndarray
    if ".argmin(" in expr and etl == "numpy" and pctl == "scipy":
        return ("dynamic_probe",
                "probe confirms cdist() returns numpy.ndarray, "
                ".argmin() is numpy method; PCResolve says scipy (wrong_owner)")

    if ".argmin(" in expr and etl == "numpy":
        return ("static_context",
                ".argmin() on numpy ndarray")

    # scipy sparse .todense()
    if ".todense()" in expr and etl == "scipy":
        return ("dynamic_probe",
                "probe confirms .todense() __module__ is scipy.sparse._base; "
                "scipy sparse method.  PCResolve says python/local (miss)")

    # scipy sparse .toarray()
    if ".toarray()" in expr and etl == "scipy":
        return ("dynamic_probe",
                ".toarray() on scipy sparse matrix")

    # cdist() call itself
    if "cdist(" in expr:
        return ("static_obvious",
                "direct import from scipy.spatial.distance")

    # --- Conversion-related -----------------------------------------------
    # .reshape() on ndarray after conversion
    if ".reshape(" in expr and etl == "numpy":
        return ("dynamic_probe",
                "probe confirms ndarray.reshape() is numpy method "
                "after to_numpy conversion boundary")

    # .flatten() on ndarray
    if ".flatten()" in expr and etl == "numpy":
        return ("dynamic_probe",
                "probe confirms ndarray.flatten() is numpy method")

    # .T on ndarray
    if expr.endswith(".T") and etl == "numpy":
        return ("static_obvious",
                "ndarray.T attribute access is numpy")

    # .cumsum(axis=0) ndarray/Series
    if ".cumsum(" in expr:
        if etl == "numpy":
            return ("static_context", "ndarray.cumsum() is numpy method")
        if etl == "pandas":
            return ("static_context", "pandas cumsum method on Series/DataFrame")

    # --- Pandas methods on pandas objects ---------------------------------
    _pandas_methods = [".dropna(", ".to_numpy(", ".between_time(", ".resample(",
                       ".sum(", ".dot(", ".transpose(", ".drop("]
    for pm in _pandas_methods:
        if pm in expr and etl == "pandas":
            return ("static_context",
                    "pandas %s method on pandas Series/DataFrame" % pm)

    _numpy_methods = [".flatten(", ".reshape(", ".copy(", ".mean(", ".argmin(",
                      ".any(", ".sum(", ".astype(", ".tolist(", ".conj(",
                      ".diagonal(", ".real"]
    for nm in _numpy_methods:
        if nm in expr and etl == "numpy":
            return ("static_context",
                    "numpy %s method on numpy ndarray" % nm)

    # --- Framework public receiver surface --------------------------------
    if "request.headers" in expr:
        return ("static_context",
                "framework public receiver surface; Flask request.headers "
                "is a documented public attribute")
    if "app.logger" in expr:
        return ("static_context",
                "framework public receiver surface; Flask app.logger "
                "is a documented public attribute")
    if "app.run(" in expr:
        return ("static_context",
                "framework public method; Flask app.run()")
    if "app.test_client()" in expr:
        return ("static_context",
                "framework public method; Flask test_client() returns FlaskClient")
    if "client.get(" in expr or "client.post(" in expr or "client.put(" in expr:
        return ("static_context",
                "framework public receiver surface; FlaskClient method, "
                "receiver from app.test_client()")

    # --- Specific known patterns ------------------------------------------
    # _preaverage() return -> .flatten()
    if "_preaverage" in expr:
        return ("dynamic_probe",
                "probe confirms _preaverage operates on ndarray, "
                "returns ndarray-like; .flatten() is numpy")

    # refresh_time() return -> .dropna()
    if "refresh_time" in expr:
        return ("static_context",
                "refresh_time returns pandas DataFrame; .dropna() is pandas method")

    # pd.Series constructor
    if "pd.Series(" in expr:
        return ("static_obvious",
                "direct pandas constructor call")

    # pd.DataFrame constructor
    if "pd.DataFrame(" in expr:
        return ("static_obvious",
                "direct pandas constructor call")

    # np.random.normal() result methods
    if "np.random.normal" in expr:
        return ("static_obvious",
                "direct numpy API call")

    # np.diag, np.zeros, etc.
    for np_func in ["np.diag(", "np.zeros(", "np.ones(", "np.empty(",
                    "np.concatenate(", "np.einsum(", "np.linalg.",
                    "np.where(", "np.isnan(", "np.argmax(", "np.amax(",
                    "np.exp(", "np.sum(", "np.sqrt(", "np.abs(",
                    "np.diff(", "np.minimum(", "np.ceil(", "np.power(",
                    "np.dot(", "np.column_stack(", "np.flip(", "np.arange(",
                    "np.log("]:
        if np_func in expr:
            return ("static_obvious", "direct numpy API call")

    # sns.heatmap
    if "sns." in expr:
        return ("static_obvious", "direct seaborn API call")

    # animation.FuncAnimation
    if "animation." in expr:
        return ("static_obvious", "direct matplotlib API call")

    # sim.Universe constructor
    if "sim.Universe(" in expr:
        return ("static_obvious", "local module constructor call")

    # X[c].mean(axis=0) — numpy indexing + method
    if "].mean(" in expr and etl == "numpy":
        return ("static_context",
                "numpy indexing result .mean() is numpy method")

    # ndarray .copy()
    if ".copy()" in expr and etl == "numpy":
        return ("static_obvious", "ndarray.copy() is numpy method")

    # pickle.dump / open / gensim
    if "pickle." in expr or "gensim." in expr:
        return ("static_obvious", "direct import-backed API call")

    # str conversion, sorted, zip, operator, range
    for builtin_func in ["str(", "sorted(", "zip(", "range(", "open(",
                          "int(", "float(", "operator."]:
        if builtin_func in expr:
            return ("static_obvious", "Python builtin call")

    # collections.defaultdict
    if "defaultdict" in expr:
        return ("static_obvious", "direct collections import")

    # ValueError, etc.
    if "ValueError(" in expr or "Exception(" in expr:
        return ("static_obvious", "Python builtin exception")

    # print
    if expr.startswith("print("):
        return ("static_obvious", "Python builtin print()")

    # np.float16(X) wrapper
    if "np.float16(" in expr or "np.float64(" in expr:
        return ("static_obvious", "numpy dtype wrapper")

    # pandas .shift()
    if ".shift(" in expr and etl == "pandas":
        return ("static_context", "pandas .shift() method on Series/DataFrame")

    # pandas .values.flatten() — values is conversion boundary
    if ".values.flatten()" in expr:
        return ("dynamic_probe",
                "probe confirms .values converts to ndarray, "
                ".flatten() is numpy method after conversion boundary")

    # ndarray .ravel()
    if ".ravel()" in expr and etl == "numpy":
        return ("static_context", "ndarray.ravel() is numpy method")

    # matplotlib.pyplot
    if "plt.figure(" in expr or "plt.clf(" in expr or "plt.show(" in expr:
        return ("static_obvious", "direct matplotlib.pyplot API call")

    # scipy.sparse.issparse
    if "issparse(" in expr:
        return ("static_obvious", "direct scipy.sparse API call")

    # pyprind / progress bar — receiver from ProgBar() constructor
    if ".update()" in expr and "prbar" in expr.lower():
        return ("static_context",
                "receiver ownership inferred from pyprind.ProgBar() return")

    # remaining unmatched transitive — depends on receiver provenance
    return ("static_context",
            "transitive method; receiver ownership inferred through "
            "return-value propagation or import chain")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def add_levels(proj_name, dry_run=False):
    """Load JSONL, classify each record, write back."""
    path = os.path.join(CALLS_DIR, proj_name + ".jsonl")
    if not os.path.exists(path):
        print("SKIP %s: JSONL not found" % proj_name)
        return None

    # Skip locked projects — their verification levels are final.
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        manifest = json.load(f).get("projects", {})
    if manifest.get(proj_name, {}).get("status") == "locked":
        print("SKIP %s: already locked" % proj_name)
        return None

    with open(path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    stats = {"total": len(records)}
    for rec in records:
        level, vnotes = _classify(rec)

        # P1 guard: RETURN_PROPAGATION and UNRESOLVED can never be
        # static_obvious.  These depend on receiver provenance or
        # are not yet statically resolvable.
        if rec.get("pcresolve_reason") == "UNRESOLVED":
            if level == "static_obvious":
                level = "manual_reasoned"
                vnotes = ("unresolved receiver; unknown owner "
                          "requires manual confirmation")
        if (rec.get("pcresolve_reason") == "RETURN_PROPAGATION"
                and level == "static_obvious"):
            level = "static_context"
            vnotes = ("receiver ownership inferred through "
                      "return-value propagation")

        rec["verification_level"] = level
        rec["verification_notes"] = vnotes
        stats[level] = stats.get(level, 0) + 1

    if not dry_run:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return stats


def check_lock(proj_name):
    """Check if a project meets lock readiness or locked integrity criteria.

    For reviewed pilots: checks lock readiness (ready to transition).
    For locked pilots:  checks integrity (still valid after lock).
    Returns a dict with 'ok', 'status', 'blockers', etc.
    """
    path = os.path.join(CALLS_DIR, proj_name + ".jsonl")
    if not os.path.exists(path):
        return None

    with open(path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    # Read projects.json expected status
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        manifest = json.load(f)["projects"]
    manifest_status = manifest.get(proj_name, {}).get("status", "")

    result = {
        "project": proj_name,
        "total": len(records),
        "positive": 0,
        "negative": 0,
        "ambiguous": 0,
        "unsupported": 0,
        "no_verification_level": 0,
        "no_verification_notes": 0,
        "levels": {},
        "ok": True,
        "blockers": [],
        "state": "",  # "reviewed" or "locked"
    }

    ann_statuses = set()
    for rec in records:
        status = rec.get("status", "")
        ann_status = rec.get("annotation_status", "")
        ann_statuses.add(ann_status)
        level = rec.get("verification_level", "")
        vnotes = rec.get("verification_notes", "")

        if status == "positive":
            result["positive"] += 1
            if not level:
                result["no_verification_level"] += 1
                result["ok"] = False
                result["blockers"].append(
                    "missing verification_level at %s:%d:%d %s" % (
                        rec.get("file", ""), rec.get("lineno", 0),
                        rec.get("col_offset", 0),
                        rec.get("expression", "")[:60]))
            else:
                result["levels"][level] = result["levels"].get(level, 0) + 1
                if level == "unsupported":
                    result["ok"] = False
                    result["blockers"].append(
                        "verification_level='unsupported' at %s:%d:%d %s" % (
                            rec.get("file", ""), rec.get("lineno", 0),
                            rec.get("col_offset", 0),
                            rec.get("expression", "")[:60]))
            if not vnotes:
                result["no_verification_notes"] += 1
                result["ok"] = False
                result["blockers"].append(
                    "missing verification_notes at %s:%d:%d %s" % (
                        rec.get("file", ""), rec.get("lineno", 0),
                        rec.get("col_offset", 0),
                        rec.get("expression", "")[:60]))

            # P1 guard: RETURN_PROPAGATION requires >= static_context.
            if (rec.get("pcresolve_reason") == "RETURN_PROPAGATION"
                    and level == "static_obvious"):
                result["ok"] = False
                result["blockers"].append(
                    "RETURN_PROPAGATION requires static_context or "
                    "stronger at %s:%d:%d %s" % (
                        rec.get("file", ""), rec.get("lineno", 0),
                        rec.get("col_offset", 0),
                        rec.get("expression", "")[:60]))

            # P1 guard: UNRESOLVED requires >= manual_reasoned.
            if (rec.get("pcresolve_reason") == "UNRESOLVED"
                    and level == "static_obvious"):
                result["ok"] = False
                result["blockers"].append(
                    "UNRESOLVED requires manual_reasoned or "
                    "stronger at %s:%d:%d %s" % (
                        rec.get("file", ""), rec.get("lineno", 0),
                        rec.get("col_offset", 0),
                        rec.get("expression", "")[:60]))
        elif status == "negative":
            result["negative"] += 1
        elif status == "ambiguous":
            result["ambiguous"] += 1
        elif status == "unsupported":
            result["unsupported"] += 1

    if result["unsupported"] > 0:
        result["ok"] = False
        result["blockers"].append(
            "%d status='unsupported' records (must be 0)" % result["unsupported"])

    # Annotation status gate: reviewed means lock-ready, locked means integrity
    valid_ann = {"reviewed", "locked"}
    if not ann_statuses <= valid_ann or len(ann_statuses) != 1:
        result["ok"] = False
        result["blockers"].append(
            "annotation_status must be uniformly 'reviewed' or 'locked', got: %s"
            % sorted(ann_statuses))
    else:
        result["state"] = list(ann_statuses)[0]

    # Schema invariant: record["project"] must match JSONL project name.
    for rec in records:
        if rec.get("project") != proj_name:
            result["ok"] = False
            result["blockers"].append(
                "project field mismatch: expected=%s got=%s at %s:%d:%d %s" % (
                    proj_name, rec.get("project"),
                    rec.get("file", ""), rec.get("lineno", 0),
                    rec.get("col_offset", 0),
                    rec.get("expression", "")[:60]))

    # Schema type gate: list-typed fields must actually be lists
    _list_fields = (
        "expected_alternatives", "expected_decorated_by",
        "pcresolve_alternatives", "pcresolve_decorated_by",
    )
    for rec in records:
        for field in _list_fields:
            value = rec.get(field)
            if value is not None and not isinstance(value, list):
                result["ok"] = False
                result["blockers"].append(
                    "%s must be a list (got %s) at %s:%d:%d %s" % (
                        field, type(value).__name__,
                        rec.get("file", ""), rec.get("lineno", 0),
                        rec.get("col_offset", 0),
                        rec.get("expression", "")[:60]))

    # Cross-check with projects.json
    if result["state"] and manifest_status != result["state"]:
        result["ok"] = False
        result["blockers"].append(
            "projects.json status='%s' but JSONL annotation_status='%s'"
            % (manifest_status, result["state"]))

    if result["state"] == "reviewed":
        result["action"] = "Run with --lock to set annotation_status=locked"
    elif result["state"] == "locked":
        result["action"] = "Locked integrity passed"

    return result


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_stats(project_stats):
    print("%-12s %5s  %s" % ("Project", "Total", "Level Breakdown"))
    print("-" * 60)
    for proj, stats in project_stats.items():
        if stats is None:
            continue
        breakdown = ", ".join("%s=%d" % (k, v)
                              for k, v in sorted(stats.items())
                              if k != "total")
        print("%-12s %5d  %s" % (proj, stats["total"], breakdown))


def print_lock_check(lock_results):
    print("")
    print("=" * 60)
    print("LOCK STATUS CHECK")
    print("=" * 60)
    print("")
    print("Checks: all positive have verification_level + verification_notes,")
    print("        unsupported=0 (both status and verification_level),")
    print("        annotation_status uniformly reviewed or locked,")
    print("        projects.json status matches JSONL.")
    print("")
    print("%-12s %6s %4s %4s %4s %4s %-8s %s" % (
        "Project", "Total", "Pos", "Neg", "Amb", "Unsup", "State", "OK"))
    print("-" * 60)
    all_ok = True
    for r in lock_results:
        if r is None:
            continue
        print("%-12s %6d %4d %4d %4d %4d %-8s %s" % (
            r["project"], r["total"], r["positive"], r["negative"],
            r["ambiguous"], r["unsupported"],
            r.get("state", "?"),
            "YES" if r["ok"] else "NO"))
        if not r["ok"]:
            all_ok = False
            for b in r["blockers"]:
                print("  BLOCKER: %s" % b)
        if r.get("action"):
            print("  ACTION:  %s" % r["action"])

    if all_ok:
        print("")
        print("All pilots pass.  No blockers.")
        reviewed = [r for r in lock_results if r and r.get("state") == "reviewed"]
        if reviewed:
            print("Run with --lock to set annotation_status=locked.")
    else:
        print("")
        print("Some pilots have blockers.  Fix above.")
    return all_ok


def do_lock(proj_name):
    """Set annotation_status to locked for a reviewed project."""
    path = os.path.join(CALLS_DIR, proj_name + ".jsonl")
    if not os.path.exists(path):
        return

    check = check_lock(proj_name)
    if check is None:
        print("SKIP %s: cannot check" % proj_name)
        return

    if check.get("state") == "locked":
        print("SKIP %s: already locked" % proj_name)
        return

    if check.get("state") != "reviewed":
        print("SKIP %s: must be uniformly 'reviewed', got '%s'"
              % (proj_name, check.get("state", "?")))
        return

    if not check["ok"]:
        print("SKIP %s: has blockers, fix before locking" % proj_name)
        return

    with open(path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    for rec in records:
        rec["annotation_status"] = "locked"

    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # Update projects.json
    with open(PROJECTS_FILE, encoding="utf-8") as f:
        manifest = json.load(f)

    if proj_name in manifest["projects"]:
        manifest["projects"][proj_name]["status"] = "locked"
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
            f.write("\n")

    print("LOCKED: %s" % proj_name)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Add verification_level to GT records and check lock readiness")
    parser.add_argument("--check", action="store_true",
                        help="Only check lock readiness (no writes)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Classify but do not write JSONL")
    parser.add_argument("--lock", action="store_true",
                        help="Set annotation_status=locked for lockable pilots")
    parser.add_argument("--project", action="append", default=[],
                        help="Only process this project (repeatable)")
    ns = parser.parse_args()

    with open(PROJECTS_FILE, encoding="utf-8") as f:
        manifest = json.load(f)["projects"]

    pilot_names = [n for n, info in manifest.items()
                   if info.get("tier") == "pilot"]

    # Validate --project values
    if ns.project:
        all_names = set(manifest.keys())
        pilot_set = set(pilot_names)
        unknown = [n for n in ns.project if n not in all_names]
        non_pilot = [n for n in ns.project if n in all_names and n not in pilot_set]
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
        pilot_names = [n for n in pilot_names if n in ns.project]
        if not pilot_names:
            print("ERROR: no pilot projects matched", file=sys.stderr)
            return 1

    if not ns.check and not ns.lock:
        # Classify mode
        project_stats = {}
        for name in pilot_names:
            stats = add_levels(name, dry_run=ns.dry_run)
            project_stats[name] = stats
        print_stats(project_stats)
        if ns.dry_run:
            print("\nDRY RUN: no files modified.")
        else:
            print("\nverification_level written to JSONL files.")

    # Always check lock readiness after classification (or standalone)
    lock_results = []
    for name in pilot_names:
        result = check_lock(name)
        lock_results.append(result)
    all_ok = print_lock_check(lock_results)

    if ns.lock:
        for name in pilot_names:
            do_lock(name)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
