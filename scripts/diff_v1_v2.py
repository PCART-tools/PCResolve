#!/usr/bin/env python3
## @package scripts.diff_v1_v2
#  Compare v1 vs v2 analysis results on a project.
#
#  Usage:
#    python scripts/diff_v1_v2.py tests/fixtures/tested_projects/Deep-Graph-Kernels
#    python scripts/diff_v1_v2.py tests/fixtures/tested_projects/

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve.cross_file import analyze_project


def run(model, path):
    t0 = time.perf_counter()
    result = analyze_project(path, scope_model=model)
    elapsed = time.perf_counter() - t0
    return result, elapsed


def compare(path):
    v1, t1 = run("v1", path)
    v2, t2 = run("v2", path)

    v1_calls = {(c.file_path, c.lineno, c.col_offset, c.expression): c.top_library
                for c in v1.all_api_calls}
    v2_calls = {(c.file_path, c.lineno, c.col_offset, c.expression): c.top_library
                for c in v2.all_api_calls}

    v1_syms = {(p.file_path, p.lineno, p.col_offset, p.symbol, p.kind): p.top_library
               for p in v1.all_symbol_provenance}
    v2_syms = {(p.file_path, p.lineno, p.col_offset, p.symbol, p.kind): p.top_library
               for p in v2.all_symbol_provenance}

    # Classify API call differences
    call_regressions = []
    call_improvements = []
    call_precision = []
    call_same = 0
    for key in v1_calls:
        v1_top = v1_calls[key]
        v2_top = v2_calls.get(key)
        if v2_top is None:
            continue
        if v2_top == v1_top:
            call_same += 1
        elif v2_top in ("local", "unknown", "") and v1_top not in ("local", "unknown", ""):
            call_regressions.append((key, v1_top, v2_top))
        elif v1_top in ("local", "unknown", "") and v2_top not in ("local", "unknown", ""):
            call_improvements.append((key, v1_top, v2_top))
        elif v1_top not in ("local", "unknown", "") and v2_top not in ("local", "unknown", ""):
            call_precision.append((key, v1_top, v2_top))
        else:
            call_regressions.append((key, v1_top, v2_top))

    only_v2_calls = set(v2_calls.keys()) - set(v1_calls.keys())

    # Compare library usage
    v1_libs = set(v1.library_usage.keys())
    v2_libs = set(v2.library_usage.keys())
    v2_only_libs = v2_libs - v1_libs

    print("Project: %s" % os.path.abspath(path))
    print("v1 time: %.3fs, v2 time: %.3fs" % (t1, t2))
    print()

    print("API Calls: v1=%d v2=%d same=%d regressions=%d improvements=%d precision=%d only_v2=%d" % (
        len(v1_calls), len(v2_calls), call_same, len(call_regressions),
        len(call_improvements), len(call_precision), len(only_v2_calls)))

    if call_regressions:
        print("\nRegressions (v1 third-party -> v2 local/unknown):")
        for key, v1t, v2t in call_regressions[:20]:
            print("  %s:%d:%d %s: %s -> %s" % (key[0], key[1], key[2], key[3], v1t, v2t))

    if call_improvements:
        print("\nImprovements (v1 local -> v2 third-party):")
        for key, v1t, v2t in call_improvements[:10]:
            print("  %s:%d:%d %s: %s -> %s" % (key[0], key[1], key[2], key[3], v1t, v2t))

    if call_precision:
        print("\nPrecision changes (third-party -> another third-party, e.g. SourceSet alternatives):")
        for key, v1t, v2t in call_precision[:10]:
            print("  %s:%d:%d %s: %s -> %s" % (key[0], key[1], key[2], key[3], v1t, v2t))

    print("\nLibraries: v1=%d v2=%d v2_only=%d" % (
        len(v1_libs), len(v2_libs), len(v2_only_libs)))
    if v2_only_libs:
        illegal = {l for l in v2_only_libs if "(" in l or "[" in l}
        if illegal:
            print("  Illegal library keys: %s" % sorted(illegal))

    # Symbol provenance comparison
    v1_sym_count = len(v1_syms)
    v2_sym_count = len(v2_syms)
    print("\nSymbol Provenance: v1=%d v2=%d" % (v1_sym_count, v2_sym_count))

    # Check for illegal library keys in v2 library_usage
    illegal_libs = [lib for lib in v2.library_usage if _is_illegal_key(lib)]
    # Check full facts for internal IR leaks
    illegal_calls = [c for c in v2.all_api_calls if _is_illegal_key(c.top_library)]
    illegal_provs = [p for p in v2.all_symbol_provenance
                     if _is_illegal_key(p.top_library)]
    illegal = len(illegal_libs) + len(illegal_calls) + len(illegal_provs)
    if illegal:
        if illegal_libs:
            print("  Illegal library_usage keys: %s" % sorted(illegal_libs))
        if illegal_calls:
            print("  Illegal ApiCall.top_library: %d entries" % len(illegal_calls))
        if illegal_provs:
            print("  Illegal SymbolProvenance.top_library: %d entries" % len(illegal_provs))

    return len(call_regressions), illegal, len(v2_only_libs)


def _is_illegal_key(name):
    """Check if a library name looks like a dataclass repr or SourceSet display."""
    for prefix in ("InstanceMethod(", "CallResult(", "ContainerItem(",
                   "ContainerIter(", "UnknownSource(", "SourceSet("):
        if name.startswith(prefix):
            return True
    if isinstance(name, str) and name.startswith("[") and "SourceSet" in name:
        return True
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/diff_v1_v2.py <project_dir> [...]",
              file=sys.stderr)
        sys.exit(1)

    paths = []
    for arg in sys.argv[1:]:
        if not os.path.exists(arg):
            print("Not found: %s" % arg, file=sys.stderr)
            continue
        # If a directory contains subdirectories each with .py files,
        # treat them as individual projects.
        if os.path.isdir(arg):
            subdirs = [os.path.join(arg, d) for d in os.listdir(arg)
                       if os.path.isdir(os.path.join(arg, d))]
            py_files = [f for f in os.listdir(arg) if f.endswith('.py')
                        and os.path.isfile(os.path.join(arg, f))]
            if subdirs and not py_files:
                paths.extend(sorted(subdirs))
            else:
                paths.append(arg)
        else:
            paths.append(arg)

    total_regressions = 0
    total_illegal = 0
    summary_lines = []
    for path in paths:
        regs, illegal_count, _ = compare(path)
        total_regressions += regs
        total_illegal += illegal_count
        summary_lines.append("%s: regressions=%d" % (
            os.path.basename(path), regs))
        print()

    print("SUMMARY")
    for line in summary_lines:
        print("  %s" % line)
    print("  TOTAL regressions: %d" % total_regressions)
    print("  TOTAL illegal keys: %d" % total_illegal)

    if total_regressions or total_illegal:
        sys.exit(1)


if __name__ == "__main__":
    main()
