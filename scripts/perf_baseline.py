#!/usr/bin/env python3
## @package scripts.perf_baseline
#  Performance baseline for pcresolve analysis.
#
#  Usage:
#    python scripts/perf_baseline.py tests/fixtures/tested_projects/polire
#    python scripts/perf_baseline.py tests/fixtures/tested_projects/

import json
import os
import sys
import time
import tracemalloc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from pcresolve import analyze_project


def run_baseline(project_root):
    tracemalloc.start()
    t0 = time.perf_counter()
    result = analyze_project(project_root)
    elapsed = time.perf_counter() - t0
    _current, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    n_files = len(result.files)
    n_calls = len(result.all_api_calls)
    n_diag = len(getattr(result, "diagnostics", []))  # populated in phase 1
    files_per_sec = n_files / elapsed if elapsed > 0 else 0.0

    return {
        "project": project_root,
        "files": n_files,
        "calls": n_calls,
        "seconds": round(elapsed, 3),
        "files_per_sec": round(files_per_sec, 1),
        "peak_memory_bytes": peak_bytes,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/perf_baseline.py <project_dir> [...]", file=sys.stderr)
        sys.exit(1)

    for path in sys.argv[1:]:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            print(json.dumps({"project": path, "error": "not_found"}))
            continue
        record = run_baseline(path)
        print(json.dumps(record))


if __name__ == "__main__":
    main()
