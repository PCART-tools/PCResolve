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

def _print_json_summary(result, top=20):
    v = build_summary_view(result, top=top)
    print(json.dumps(v, indent=2, ensure_ascii=False))


def _print_json_full(result):
    v = build_full_view(result)
    print(json.dumps(v, indent=2, ensure_ascii=False))


# ── main ─────────────────────────────────────────────────────────────────

def _flow_text(result):
    lines = ['Value flow (experimental %s)' % result.schema_version,
             'Entry: %s:%s' % (result.entry.module, result.entry.qualname),
             'Functions: %d; call sites: %d' % (len(result.functions), len(result.calls))]
    for call in result.calls:
        lines.append('\n%s:%d:%d %s' % (call.caller.file_path, call.lineno,
                                         call.col_offset, call.callee_name))
        lines.append('  Parameter flows:')
        for flow in call.parameter_flows:
            lines.append('    %s -> %s -> %s (%s)' % (
                flow['source_parameter'], flow['argument'],
                flow['target_parameter'] or '<unresolved formal>', flow['relation']))
        if not call.parameter_flows:
            lines.append('    No flow found (not a proof of absence).')
        lines.append('  Return flows: %d path(s) to caller return' % len(call.return_flows))
        for flow in call.return_flows:
            lines.append('    %s: %s' % (flow['relation'], ' -> '.join(
                e.get('source_text', '') for e in flow['evidence'])))
    lines.append('\nBoundaries: %d' % len(result.boundaries))
    for boundary in result.boundaries:
        lines.append('  ' + json.dumps(boundary, ensure_ascii=False))
    return '\n'.join(lines)


def _run_value_flow(parser, args, project_root):
    from .flow import FlowAnalyzer, FunctionRef

    if (args.json_summary or args.json_full or args.json_stable or args.debug_dump
            or args.verbose or args.strict or args.usage_summary or args.quiet
            or args.explain_library or args.explain_symbol or args.explain_call
            or args.top != 20):
        parser.error('Ownership output options cannot be combined with --value-flow; use --json.')
    if not args.entry or args.entry.count(':') != 1:
        parser.error('--value-flow requires --entry MODULE:QUALNAME')
    module, qualname = args.entry.split(':')
    if not module or not qualname or not all(p.isidentifier() for p in (module + '.' + qualname).split('.')):
        parser.error('--entry must be MODULE:QUALNAME with dotted Python identifiers')
    if bool(project_root) == bool(args.source_file):
        parser.error('Specify either project_root or one or more --source-file paths')
    if project_root and not os.path.isdir(project_root):
        parser.error('Project root is not a directory: %s' % project_root)
    for path in args.source_file or []:
        if not os.path.isfile(path) or not path.endswith(('.py', '.pyi')):
            parser.error('Source must be an existing .py or .pyi file: %s' % path)
    for root in args.import_root or []:
        if not os.path.isdir(root):
            parser.error('Import root is not a directory: %s' % root)
    depth = args.depth if args.depth is not None else 1
    functions = args.max_functions if args.max_functions is not None else 500
    calls = args.max_call_contexts if args.max_call_contexts is not None else 2000
    if min(depth, functions, calls) < 1:
        parser.error('Depth and budgets must be positive integers')
    try:
        analyzer = FlowAnalyzer(project_root=project_root,
                                source_files=args.source_file, import_roots=args.import_root)
        result = analyzer.analyze(FunctionRef(module=module, qualname=qualname),
                                  max_depth=depth, max_functions=functions,
                                  max_call_contexts=calls)
        payload = json.dumps(result.to_dict(), ensure_ascii=False, indent=2) if args.json else _flow_text(result)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as stream:
                stream.write(payload + '\n')
        else:
            print(payload)
    except (OSError, ValueError) as error:
        parser.error(str(error))


## Run ownership analysis or the opt-in experimental value-flow CLI.
def main():
    parser = argparse.ArgumentParser(
        description=(
            "Classify Python API call ownership and trace library usage "
            "provenance."
        )
    )
    parser.add_argument("project_root", nargs="?", default=None,
                        help="Absolute path to the project root directory.")
    parser.add_argument("--json", action="store_true",
                        help="Full provenance JSON, or flow JSON with --value-flow.")
    parser.add_argument("--json-summary", action="store_true",
                        help="Summary JSON profile (small, stable, for CI).")
    parser.add_argument("--json-full", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--json-stable", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--debug-dump", action="store_true",
                        help="Full text output (old default, for debugging).")
    parser.add_argument("--stdin", action="store_true",
                        help="Read project root path from stdin.")
    parser.add_argument("--verbose", action="store_true",
                        help="Print diagnostics in human-readable mode.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero when error diagnostics are present.")
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
    flow = parser.add_argument_group('experimental value flow')
    flow.add_argument('--value-flow', action='store_true', help='Analyze parameter and return value flows.')
    flow.add_argument('--entry', help='Entry function as MODULE:QUALNAME (value flow only).')
    flow.add_argument('--source-file', action='append', help='Explicit Python source file; repeat instead of project_root.')
    flow.add_argument('--import-root', action='append', help='Module mapping root; repeat as needed (does not add sources).')
    flow.add_argument('--depth', type=int, help='Call-edge depth, default 1 (value flow only).')
    flow.add_argument('--max-functions', type=int, help='Function summary budget, default 500.')
    flow.add_argument('--max-call-contexts', type=int, help='Collected call-site budget, default 2000.')
    flow.add_argument('--output', help='Write flow output to a UTF-8 file instead of stdout; overwrites existing file.')
    args = parser.parse_args()

    project_root = args.project_root
    if args.stdin:
        project_root = sys.stdin.readline().strip()

    if args.value_flow:
        _run_value_flow(parser, args, project_root)
        return
    if any(value is not None for value in (args.entry, args.source_file, args.import_root,
           args.depth, args.max_functions, args.max_call_contexts, args.output)):
        parser.error('Value-flow options require --value-flow')

    if not project_root:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(project_root):
        print("Error: %s does not exist." % project_root, file=sys.stderr)
        sys.exit(1)

    result = analyze_project(project_root)

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
    elif args.json_full or args.json_stable or args.json:
        # 1.0.4+: --json, --json-full, --json-stable all emit full provenance.
        _print_json_full(result)

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
