## @package pcresolve.cli
#  Provide command-line entry point for the pcresolve tool.
#
#  Usage:
#    pcresolve /path/to/project
#    pcresolve /path/to/a.py
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


## Print diagnostics once, respecting quiet mode.
#  @param result ProjectAnalysis result.
#  @param quiet Show only error diagnostics.
#  @param verbose Include the number of skipped modules.
#  @param leading_newline Separate diagnostics from preceding text output.
def _print_diagnostics(result, quiet=False, verbose=False, leading_newline=True):
    diagnostics = [d for d in result.diagnostics if not quiet or d.severity == "error"]
    printed = False
    if diagnostics:
        if quiet:
            print(("\n" if leading_newline else "") +
                  "Diagnostics (%d errors):" % len(diagnostics))
        else:
            print(("\n" if leading_newline else "") + "Diagnostics")
        for d in diagnostics:
            loc = " (L%d:C%d)" % (d.lineno, d.col_offset) if d.lineno else ""
            print("  [%s] %s %s%s: %s" % (
                d.severity.upper(), d.code, d.file_path, loc, d.message))
        printed = True
    if verbose and result.diagnostics:
        print(("\n" if leading_newline or printed else "") +
              "%d file(s) skipped." % result.stats.get("skipped_modules", 0))
        printed = True
    return printed


## Print library usage with a limit on displayed libraries.
#  @param result ProjectAnalysis result.
#  @param top Maximum libraries to list (0 = unlimited).
#  @param leading_newline Separate this view from preceding text output.
#  @return True if a summary was printed.
def _print_usage_summary(result, top=20, leading_newline=True):
    if not result.library_usage:
        return False
    print(("\n" if leading_newline else "") + "Library Usage Summary:")
    items = sorted(result.library_usage.items())
    if top > 0:
        items = items[:top]
    for lib, u in items:
        print("\n%s" % lib)
        print("  files: %d" % len(u.files))
        print("  api calls: %d" % u.api_call_count)
        print("  symbols: %d" % u.symbol_count)
        if u.imports:
            print("  imports: %s" % ", ".join(u.imports))
    return True


def _print_explain_library(result, lib, top=20):
    v = build_explain_library_view(result, lib, top=top)
    print("Library: %s" % lib)
    if not v:
        print("No matches found for library: %s" % lib)
        return
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

## Validate ownership output options before analysis.
#  @param parser ArgumentParser used to report invalid combinations.
#  @param args Parsed CLI options.
#  @return Pair indicating JSON and explain output modes.
def _validate_output_options(parser, args):
    json_flags = [flag for flag in ("--json", "--json-full", "--json-stable")
                  if getattr(args, flag[2:].replace("-", "_"))]
    modes = ["/".join(json_flags)] if json_flags else []
    if args.json_summary:
        modes.append("--json-summary")
    if args.debug_dump:
        modes.append("--debug-dump")
    explain_flags = []
    for flag in ("--explain-library", "--explain-symbol", "--explain-call"):
        query = getattr(args, flag[2:].replace("-", "_"))
        if query is not None:
            if not query.strip():
                parser.error("%s requires a non-empty name" % flag)
            modes.append(flag)
            explain_flags.append(flag)
    if len(modes) > 1:
        parser.error("Output modes are mutually exclusive: %s" % ", ".join(modes))
    json_mode = bool(json_flags or args.json_summary)
    explain_mode = bool(explain_flags)
    for flag in ("--quiet", "--verbose", "--usage-summary"):
        if getattr(args, flag[2:].replace("-", "_")) and json_mode:
            parser.error("%s cannot be combined with JSON output" % flag)
    if explain_mode:
        if args.quiet:
            parser.error("--quiet cannot be combined with explain output")
        if args.usage_summary:
            parser.error("--usage-summary cannot be combined with explain output")
    if args.debug_dump and args.quiet:
        parser.error("--quiet cannot be combined with --debug-dump")
    if args.top is not None:
        if json_flags:
            parser.error("--top cannot be combined with %s" % json_flags[0])
        if args.debug_dump and not args.usage_summary:
            parser.error("--top cannot be combined with --debug-dump")
    return json_mode, explain_mode


## Resolve the positional or stdin-selected input path.
#  @param parser ArgumentParser used to report invalid combinations.
#  @param args Parsed CLI options.
#  @return Selected path, or None when explicit value-flow sources may be used.
def _resolve_input_path(parser, args):
    if args.stdin and args.project_root:
        parser.error("Specify either an input path or --stdin")
    if args.stdin and args.source_file:
        parser.error("Specify either --stdin or one or more --source-file paths")
    if not args.stdin:
        return args.project_root
    path = sys.stdin.readline().strip()
    if not path:
        parser.error("--stdin did not provide an input path")
    return path


## Validate value-flow-only arguments that do not depend on input contents.
#  @param parser ArgumentParser used to report invalid combinations.
#  @param args Parsed CLI options.
def _validate_value_flow_options(parser, args):
    if (args.json_summary or args.json_full or args.json_stable or args.debug_dump
            or args.verbose or args.strict or args.usage_summary or args.quiet
            or any(value is not None for value in
                   (args.explain_library, args.explain_symbol, args.explain_call))
            or args.top is not None):
        parser.error('Ownership output options cannot be combined with --value-flow; use --json.')
    if not args.entry or args.entry.count(':') != 1:
        parser.error('--value-flow requires --entry MODULE:QUALNAME')
    module, qualname = args.entry.split(':')
    if not module or not qualname or not all(
            part.isidentifier() for part in (module + '.' + qualname).split('.')):
        parser.error('--entry must be MODULE:QUALNAME with dotted Python identifiers')
    values = [value for value in
              (args.depth, args.max_functions, args.max_call_contexts)
              if value is not None]
    if values and min(values) < 1:
        parser.error('Depth and budgets must be positive integers')


def _flow_text(result):
    lines = ['Value flow (experimental %s)' % result.schema_version,
             'Entry: %s:%s' % (result.entry.module, result.entry.qualname),
             'Functions: %d; call sites: %d' % (len(result.functions), len(result.calls))]
    for call in result.calls:
        lines.append('\n%s:%d:%d %s' % (call.caller.file_path, call.lineno,
                                         call.col_offset, call.callee_name))
        lines.append('  Parameter flows:')
        lines.append('  Analysis: %s; target: %s' % (call.analysis_status, call.target_status))
        if call.receiver_sources:
            lines.append('  Receiver flows: %s' % ', '.join(
                '%s (%s)' % (v['source'], v['relation']) for v in call.receiver_sources))
        for flow in call.parameter_flows:
            lines.append('    %s -> %s -> %s (%s)' % (
                flow['source_parameter'], flow['argument'],
                flow['target_parameter'] or '<unresolved formal>', flow['relation']))
        if not call.parameter_flows:
            lines.append('    No flow found (not a proof of absence).')
        if call.effects:
            lines.append('  Effects: %s' % ', '.join(
                effect['kind'] for effect in call.effects))
        lines.append('  Return flows: %d path(s) to caller return' % len(call.return_flows))
        for flow in call.return_flows:
            lines.append('    %s: %s' % (flow['relation'], ' -> '.join(
                e.get('source_text', '') for e in flow['evidence'])))
    lines.append('\nBoundaries: %d' % len(result.boundaries))
    for boundary in result.boundaries:
        lines.append('  ' + json.dumps(boundary, ensure_ascii=False))
    return '\n'.join(lines)


def _run_value_flow(parser, args, input_path):
    from .flow import FlowAnalyzer, FunctionRef

    module, qualname = args.entry.split(':')
    if input_path and args.source_file:
        parser.error('Specify either an input path or one or more --source-file paths')
    if not input_path and not args.source_file:
        parser.error('Specify an input path or one or more --source-file paths')
    project_root = None
    source_files = args.source_file
    if input_path:
        if os.path.isdir(input_path):
            project_root = input_path
        elif os.path.isfile(input_path) and input_path.endswith(('.py', '.pyi')):
            source_files = [input_path]
        elif not os.path.exists(input_path):
            parser.error('%s does not exist' % input_path)
        else:
            parser.error('input must be a directory or a .py/.pyi file: %s' % input_path)
    for path in source_files or []:
        if not os.path.isfile(path) or not path.endswith(('.py', '.pyi')):
            parser.error('Source must be an existing .py or .pyi file: %s' % path)
    for root in args.import_root or []:
        if not os.path.isdir(root):
            parser.error('Import root is not a directory: %s' % root)
    depth = args.depth if args.depth is not None else 1
    functions = args.max_functions if args.max_functions is not None else 500
    calls = args.max_call_contexts if args.max_call_contexts is not None else 2000
    try:
        analyzer = FlowAnalyzer(project_root=project_root,
                                source_files=source_files, import_roots=args.import_root)
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
        allow_abbrev=False,
        description=(
            "Classify Python API call ownership and trace library usage "
            "provenance."
        )
    )
    parser.add_argument("project_root", nargs="?", default=None, metavar="path",
                        help="Project directory or one .py/.pyi source file.")
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
                        help="Read the input path from stdin instead of the positional path.")
    parser.add_argument("--verbose", action="store_true",
                        help="Include diagnostics in debug/explain output and show the skipped-file count.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero for ownership error diagnostics; display them in text modes.")
    parser.add_argument("--usage-summary", action="store_true",
                        help="Print library usage summary in text mode.")
    parser.add_argument("--quiet", action="store_true",
                        help="Suppress summary and warning diagnostics; combine with --usage-summary for library usage.")
    parser.add_argument("--top", type=int, default=None,
                        help="Limit ownership summaries and explain lists (0 = unlimited; default 20).")
    parser.add_argument("--explain-library", default=None,
                        help="Explain one library usage.")
    parser.add_argument("--explain-symbol", default=None,
                        help="Explain one symbol's provenance.")
    parser.add_argument("--explain-call", default=None,
                        help="Explain calls by exact callable name or dotted path suffix.")
    flow = parser.add_argument_group('experimental value flow')
    flow.add_argument('--value-flow', action='store_true', help='Analyze parameter and return value flows.')
    flow.add_argument('--entry', help='Entry function as MODULE:QUALNAME (value flow only).')
    flow.add_argument('--source-file', action='append', help='Explicit Python source file; repeat instead of the input path.')
    flow.add_argument('--import-root', action='append', help='Module mapping root; repeat as needed (does not add sources).')
    flow.add_argument('--depth', type=int, help='Call-edge depth, default 1 (value flow only).')
    flow.add_argument('--max-functions', type=int, help='Function summary budget, default 500.')
    flow.add_argument('--max-call-contexts', type=int, help='Collected call-site budget, default 2000.')
    flow.add_argument('--output', help='Write flow output to a UTF-8 file instead of stdout; overwrites existing file.')
    args = parser.parse_args()
    if args.top is not None and args.top < 0:
        parser.error("--top must be a non-negative integer (0 = unlimited)")
    if args.value_flow:
        _validate_value_flow_options(parser, args)
        json_mode = False
        explain_mode = False
    else:
        if any(value is not None for value in (args.entry, args.source_file, args.import_root,
               args.depth, args.max_functions, args.max_call_contexts, args.output)):
            parser.error('Value-flow options require --value-flow')
        json_mode, explain_mode = _validate_output_options(parser, args)
        args.top = 20 if args.top is None else args.top
    input_path = _resolve_input_path(parser, args)
    if args.value_flow:
        _run_value_flow(parser, args, input_path)
        return

    if not input_path:
        parser.error('an input path is required')

    if not os.path.exists(input_path):
        parser.error('%s does not exist' % input_path)

    if not (os.path.isdir(input_path)
            or (os.path.isfile(input_path) and input_path.endswith(('.py', '.pyi')))):
        parser.error('input must be a directory or a .py/.pyi file: %s' % input_path)

    result = analyze_project(input_path)

    # ── explain modes ────────────────────────────────────────────────
    text_printed = False
    if args.explain_library:
        _print_explain_library(result, args.explain_library, top=args.top)
        text_printed = True
    elif args.explain_symbol:
        _print_explain_symbol(result, args.explain_symbol, top=args.top)
        text_printed = True
    elif args.explain_call:
        _print_explain_call(result, args.explain_call, top=args.top)
        text_printed = True

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
            text_printed = True
        elif not args.quiet:
            _print_summary(result, top=args.top)
            text_printed = True
    if not json_mode:
        has_errors = any(d.severity == "error" for d in result.diagnostics)
        if args.verbose or (args.strict and has_errors) or not (args.debug_dump or explain_mode):
            text_printed = (_print_diagnostics(
                result, quiet=args.quiet, verbose=args.verbose,
                leading_newline=text_printed) or text_printed)
        if args.usage_summary:
            _print_usage_summary(result, top=args.top, leading_newline=text_printed)

    if args.strict:
        for d in result.diagnostics:
            if d.severity == "error":
                sys.exit(1)
