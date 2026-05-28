## @package pcresolve.cli
#  Provide command-line entry point for the pcresolve tool.
#
#  Usage:
#    pcresolve /path/to/project
#    pcresolve --json /path/to/project
#    pcresolve --json-summary /path/to/project
#    pcresolve --json-full /path/to/project
#    pcresolve --debug-dump /path/to/project
#    python -m pcresolve /path/to/project

import argparse
import json
import os
import sys
from .cross_file import analyze_project
from .views import (build_summary_view, build_full_view,
                     build_explain_library_view, build_explain_symbol_view,
                     build_explain_call_view)


## Format source location as a string.
#  @param call ApiCall object.
#  @return Location string like "(L42:C10-L42:C35)", or "".
def _format_location(call):
    if call.end_lineno and call.end_col_offset:
        return f"(L{call.lineno}:C{call.col_offset}-L{call.end_lineno}:C{call.end_col_offset})"
    elif call.lineno:
        return f"(L{call.lineno}:C{call.col_offset})"
    return ""


# ── legacy serializers (kept for --json backward-compat) ─────────────────

def _normalize_path(file_path, project_root):
    try:
        rel = os.path.relpath(file_path, project_root)
        if rel.startswith(".." + os.sep):
            rel = "<external>/" + rel
    except ValueError:
        rel = "<external>/" + str(file_path)
    result = rel.replace(os.sep, "/")
    if os.altsep:
        result = result.replace(os.altsep, "/")
    return result


def _stable_api_call(call, project_root):
    return {
        "expression": call.expression,
        "top_library": call.top_library,
        "base_symbol": call.base_symbol,
        "chain": call.chain,
        "file_path": _normalize_path(call.file_path, project_root),
        "lineno": call.lineno,
        "col_offset": call.col_offset,
        "end_lineno": call.end_lineno,
        "end_col_offset": call.end_col_offset,
        "func_name": call.func_name,
        "parameters": call.parameters,
        "resolved_func": call.resolved_func,
        "resolved_chain": call.resolved_chain,
        "reason": call.reason,
        "confidence": call.confidence,
        "alternatives": call.alternatives,
        "decorated_by": call.decorated_by,
    }


def _stable_symbol_provenance(p, project_root):
    return {
        "symbol": p.symbol, "kind": p.kind,
        "top_library": p.top_library, "top_libraries": p.top_libraries,
        "chain": p.chain, "scope_name": p.scope_name,
        "file_path": _normalize_path(p.file_path, project_root) if p.file_path else "",
        "lineno": p.lineno, "col_offset": p.col_offset,
        "reason": p.reason, "confidence": p.confidence,
        "alternatives": p.alternatives,
    }


def _stable_file_analysis(f, project_root):
    return {
        "file_path": _normalize_path(f.file_path, project_root),
        "module_name": f.module_name,
        "symbols": f.symbols, "chains": f.chains,
        "api_calls": [_stable_api_call(c, project_root) for c in f.api_calls],
        "diagnostics": [_stable_diagnostic(d, project_root) for d in f.diagnostics],
        "symbol_provenance": [_stable_symbol_provenance(p, project_root) for p in f.symbol_provenance],
    }


def _stable_diagnostic(d, project_root):
    return {
        "code": d.code, "message": d.message, "severity": d.severity,
        "file_path": _normalize_path(d.file_path, project_root) if d.file_path else "",
        "lineno": d.lineno, "col_offset": d.col_offset,
        "end_lineno": d.end_lineno, "end_col_offset": d.end_col_offset,
        "module_name": d.module_name,
    }


def _stable_project(result):
    return {
        "schema_version": result.schema_version,
        "project_root": _normalize_path(result.project_root, result.project_root),
        "files": [_stable_file_analysis(f, result.project_root) for f in result.files],
        "all_api_calls": [_stable_api_call(c, result.project_root) for c in result.all_api_calls],
        "diagnostics": [_stable_diagnostic(d, result.project_root) for d in result.diagnostics],
        "all_symbol_provenance": [_stable_symbol_provenance(p, result.project_root) for p in result.all_symbol_provenance],
        "library_usage": {k: _stable_library_usage(v) for k, v in result.library_usage.items()},
        "stats": result.stats,
    }


def _stable_library_usage(u):
    return {
        "library": u.library, "api_call_count": u.api_call_count,
        "symbol_count": u.symbol_count, "files": u.files, "imports": u.imports,
        "kind_counts": u.kind_counts, "has_evidence": u.has_evidence,
        "min_confidence": u.min_confidence, "max_confidence": u.max_confidence,
    }


# ── text output ──────────────────────────────────────────────────────────

def _print_debug_dump(result):
    """Legacy full text output (--debug-dump)."""
    print("Global symbol table:")
    for f in result.files:
        print(f"\n{f.module_name} module:")
        for symbol, source in sorted(f.symbols.items()):
            if source:
                print(f"  {symbol} -> {source}")
    print("\nGlobal symbol tracing chains:")
    for f in result.files:
        print(f"\n{f.module_name} module:")
        for symbol, chain in sorted(f.chains.items()):
            if chain:
                chain_str = " -> ".join(str(item) for item in chain)
                print(f"  {symbol}: {chain_str}")
    print("\nAll API calls:")
    for f in result.files:
        if f.api_calls:
            print(f"\n{f.module_name} module:")
            for call in f.api_calls:
                loc = _format_location(call)
                loc_str = f" {loc}" if loc else ""
                line = f"  {call.expression}{loc_str}  -> {call.top_library}"
                if call.resolved_func and call.resolved_func != call.func_name:
                    line += f"    resolved: {call.resolved_func}"
                print(line)


def _print_summary(result, top=20):
    """Compact summary text output (default)."""
    stats = result.stats
    libs = result.library_usage
    print("PCResolve Summary")
    print("Project: %s" % result.project_root)
    print("Scope model: %s" % stats.get("scope_model", "v1"))
    print("Files: %d parsed, %d skipped" % (
        stats.get("parsed_modules", 0), stats.get("skipped_modules", 0)))
    print("Libraries: %d" % len(libs))
    print("API calls: %d" % len(result.all_api_calls))
    diag_errors = sum(1 for d in result.diagnostics if d.severity == "error")
    diag_warns = sum(1 for d in result.diagnostics if d.severity == "warning")
    print("Diagnostics: %d errors, %d warnings" % (diag_errors, diag_warns))
    if libs:
        print("\nLibraries")
        items = sorted(libs.items())
        if top > 0:
            items = items[:top]
        for lib, u in items:
            print("  %-20s %d calls   %d symbols   %d files" % (
                lib, u.api_call_count, u.symbol_count, len(u.files)))
    if result.diagnostics:
        print("\nDiagnostics")
        for d in result.diagnostics:
            loc = ""
            if d.lineno:
                loc = " (L%d:C%d)" % (d.lineno, d.col_offset)
            print("  [%s] %s %s%s: %s" % (
                d.severity.upper(), d.code, d.file_path, loc, d.message))


def _print_explain_library(result, lib, top=20):
    v = build_explain_library_view(result, lib, top=top)
    if not v:
        print("Library not found: %s" % lib, file=sys.stderr)
        return
    print("Library: %s" % lib)
    print("API calls: %d" % v["api_call_count"])
    print("Symbols: %d" % v["symbol_count"])
    print("Files: %d" % len(v["files"]))
    print("Confidence: %.2f-%.2f" % (v.get("min_confidence", 0), v.get("max_confidence", 0)))
    if v["imports"]:
        print("Imports: %s" % ", ".join(v["imports"]))
    reason_counts = v.get("reason_counts", {})
    if reason_counts:
        print("Reasons: %s" % ", ".join(
            "%s=%d" % (r, c) for r, c in sorted(reason_counts.items())))
    file_stats = v.get("file_stats", {})
    if file_stats:
        print("\nFiles")
        for fp in sorted(file_stats):
            fs = file_stats[fp]
            print("  %-30s %d calls   %d symbols" % (fp, fs["calls"], fs["symbols"]))
    if v["top_calls"]:
        print("\nTop API calls")
        for c in v["top_calls"]:
            print("  %s:%d  %s" % (c["file_path"], c["lineno"], c["expression"]))
    if v["top_symbols"]:
        print("\nSymbol provenance")
        for p in v["top_symbols"]:
            chain_str = " -> ".join(str(x) for x in p["chain"])
            print("  %-10s %-10s %s" % (p["symbol"], p["kind"], chain_str))


def _print_explain_symbol(result, symbol, top=20):
    v = build_explain_symbol_view(result, symbol, top=top)
    print("Symbol: %s" % symbol)
    if v["matches"]:
        print("\nMatches")
        for p in v["matches"]:
            chain_str = " -> ".join(str(x) for x in p["chain"])
            print("  %s:%d  %s" % (p["file_path"], p["lineno"], p["symbol"]))
            print("    kind: %s" % p["kind"])
            print("    scope: %s" % (p.get("scope_name") or "<module>"))
            print("    top: %s" % p["top_library"])
            print("    chain: %s" % chain_str)
    else:
        print("No matches found for symbol: %s" % symbol)
    if v["related_calls"]:
        print("\nRelated calls")
        for c in v["related_calls"]:
            print("  %s:%d  %s -> %s" % (c["file_path"], c["lineno"],
                                          c["expression"], c["top_library"]))


def _print_explain_call(result, query, top=20):
    v = build_explain_call_view(result, query, top=top)
    print("Call Query: %s" % query)
    print("Matches: %d" % v["count"])
    if v["matches"]:
        for c in v["matches"]:
            chain_str = " -> ".join(str(x) for x in c["chain"])
            print("  %s:%d" % (c["file_path"], c["lineno"]))
            print("    expression: %s" % c["expression"])
            print("    top: %s" % c["top_library"])
            print("    base: %s" % c["base_symbol"])
            print("    resolved: %s" % c["resolved_func"])
            if c["chain"]:
                print("    chain: %s" % chain_str)
    else:
        print("No matching calls found for query: %s" % query)


# ── JSON output ──────────────────────────────────────────────────────────

def _print_json_legacy(result):
    def _serialize(obj):
        if hasattr(obj, '__dataclass_fields__'):
            return {k: _serialize(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {k: _serialize(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [_serialize(v) for v in obj]
        else:
            return obj
    output = _serialize(result)
    output["schema_version"] = result.schema_version
    print(json.dumps(output, indent=2, ensure_ascii=False))


def _print_json_summary(result, top=20):
    v = build_summary_view(result, top=top)
    print(json.dumps(v, indent=2, ensure_ascii=False))


def _print_json_full(result):
    v = build_full_view(result)
    print(json.dumps(v, indent=2, ensure_ascii=False))


# ── main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Trace API calls in a Python project to their origin libraries."
    )
    parser.add_argument("project_root", nargs="?", default=None,
                        help="Absolute path to the project root directory.")
    parser.add_argument("--json", action="store_true",
                        help="Legacy JSON output (backward-compatible).")
    parser.add_argument("--json-summary", action="store_true",
                        help="Summary JSON profile (small, stable, for CI).")
    parser.add_argument("--json-full", action="store_true",
                        help="Full JSON profile (schema-backed, for debugging).")
    parser.add_argument("--json-stable", action="store_true",
                        help="Alias for --json-full.")
    parser.add_argument("--debug-dump", action="store_true",
                        help="Full text output (old default, for debugging).")
    parser.add_argument("--stdin", action="store_true",
                        help="Read project root path from stdin.")
    parser.add_argument("--verbose", action="store_true",
                        help="Print diagnostics in human-readable mode.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero when error diagnostics are present.")
    parser.add_argument("--scope-model", choices=("v1", "v2"), default="v1",
                        help="Scope model: v1 (legacy), v2 (lexical scopes). Default: v1.")
    parser.add_argument("--usage-summary", action="store_true",
                        help="Print library usage summary in text mode.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress summary; show only error diagnostics and library usage.")
    parser.add_argument("--top", type=int, default=20,
                        help="Max entries in lists (0 = unlimited). Default: 20.")
    parser.add_argument("--explain-library", default=None,
                        help="Explain one library usage.")
    parser.add_argument("--explain-symbol", default=None,
                        help="Explain one symbol's provenance.")
    parser.add_argument("--explain-call", default=None,
                        help="Explain matching call expressions.")
    args = parser.parse_args()

    project_root = args.project_root
    if args.stdin:
        project_root = sys.stdin.readline().strip()

    if not project_root:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(project_root):
        print("Error: %s does not exist." % project_root, file=sys.stderr)
        sys.exit(1)

    result = analyze_project(project_root, scope_model=args.scope_model)

    # ── explain modes ────────────────────────────────────────────────
    if args.explain_library:
        _print_explain_library(result, args.explain_library, top=args.top)
    elif args.explain_symbol:
        _print_explain_symbol(result, args.explain_symbol, top=args.top)
    elif args.explain_call:
        _print_explain_call(result, args.explain_call, top=args.top)

    # ── JSON modes ───────────────────────────────────────────────────
    elif args.json_summary:
        _print_json_summary(result, top=args.top)
    elif args.json_full or args.json_stable:
        _print_json_full(result)
    elif args.json:
        _print_json_legacy(result)

    # ── text modes ───────────────────────────────────────────────────
    else:
        if args.debug_dump:
            _print_debug_dump(result)
        elif not args.quiet:
            _print_summary(result, top=args.top)
        if args.quiet:
            diag_errors = [d for d in result.diagnostics if d.severity == "error"]
            if diag_errors:
                print("Diagnostics (%d errors):" % len(diag_errors))
                for d in diag_errors:
                    loc = ""
                    if d.lineno:
                        loc = " (L%d:C%d)" % (d.lineno, d.col_offset)
                    print("  [%s] %s %s%s: %s" % (
                        d.severity.upper(), d.code, d.file_path, loc, d.message))
        if args.usage_summary and result.library_usage:
            print("\nLibrary Usage Summary:")
            for lib, u in sorted(result.library_usage.items()):
                print("\n%s" % lib)
                print("  files: %d" % len(u.files))
                print("  api calls: %d" % u.api_call_count)
                print("  symbols: %d" % u.symbol_count)
                if u.imports:
                    print("  imports: %s" % ", ".join(u.imports))
        if args.verbose and result.diagnostics:
            print("\nDiagnostics:")
            for d in result.diagnostics:
                loc = ""
                if d.lineno:
                    loc = " (L%d:C%d)" % (d.lineno, d.col_offset)
                print("  [%s] %s %s%s: %s" % (
                    d.severity.upper(), d.code, d.file_path, loc, d.message))
            print("\n%d file(s) skipped." % len(result.diagnostics))

    if args.strict:
        for d in result.diagnostics:
            if d.severity == "error":
                sys.exit(1)
