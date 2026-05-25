## @package pcresolve.cli
#  Provide command-line entry point for the pcresolve tool.
#
#  Usage:
#    pcresolve /path/to/project
#    pcresolve --json /path/to/project
#    pcresolve --json-stable /path/to/project
#    python -m pcresolve /path/to/project
#    echo /path/to/project | pcresolve --stdin

import argparse
import json
import os
import sys
from .cross_file import analyze_project


## Format source location as a string.
#  @param call ApiCall object.
#  @return Location string like "(L42:C10-L42:C35)", or "".
def _format_location(call):
    if call.end_lineno and call.end_col_offset:
        return f"(L{call.lineno}:C{call.col_offset}-L{call.end_lineno}:C{call.end_col_offset})"
    elif call.lineno:
        return f"(L{call.lineno}:C{call.col_offset})"
    return ""


## Normalize a file path to POSIX-style for stable JSON output.
#
#  Converts to a relative path. Paths outside project_root are prefixed
#  with "<external>/". Both os.sep and os.altsep are unified to "/".
#  @param file_path Absolute or relative file path.
#  @param project_root The project root directory.
#  @return Normalized POSIX-style path string.
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


## Serialize one ApiCall to a stable-ordered dict.
#  @param call ApiCall object.
#  @param project_root Project root for path normalization.
#  @return Ordered dict with versioned-schema fields.
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
    }


## Serialize one FileAnalysis to a stable-ordered dict.
#  @param f FileAnalysis object.
#  @param project_root Project root for path normalization.
#  @return Ordered dict with versioned-schema fields.
def _stable_symbol_provenance(p, project_root):
    """Serialize one SymbolProvenance to a stable-ordered dict."""
    return {
        "symbol": p.symbol,
        "kind": p.kind,
        "top_library": p.top_library,
        "top_libraries": p.top_libraries,
        "chain": p.chain,
        "scope_name": p.scope_name,
        "file_path": _normalize_path(p.file_path, project_root) if p.file_path else "",
        "lineno": p.lineno,
        "col_offset": p.col_offset,
        "reason": p.reason,
        "confidence": p.confidence,
        "alternatives": p.alternatives,
    }


def _stable_file_analysis(f, project_root):
    return {
        "file_path": _normalize_path(f.file_path, project_root),
        "module_name": f.module_name,
        "symbols": f.symbols,
        "chains": f.chains,
        "api_calls": [_stable_api_call(c, project_root) for c in f.api_calls],
        "diagnostics": [_stable_diagnostic(d, project_root) for d in f.diagnostics],
        "symbol_provenance": [_stable_symbol_provenance(p, project_root) for p in f.symbol_provenance],
    }


## Serialize ProjectAnalysis to a stable-ordered dict.
#
#  Uses fixed field order and normalized paths for deterministic output.
#  @param result ProjectAnalysis result object.
#  @return Ordered dict suitable for JSON serialization.
def _stable_diagnostic(d, project_root):
    """Serialize one Diagnostic to a stable-ordered dict."""
    return {
        "code": d.code,
        "message": d.message,
        "severity": d.severity,
        "file_path": _normalize_path(d.file_path, project_root) if d.file_path else "",
        "lineno": d.lineno,
        "col_offset": d.col_offset,
        "end_lineno": d.end_lineno,
        "end_col_offset": d.end_col_offset,
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
    """Serialize one LibraryUsage to a stable-ordered dict."""
    return {
        "library": u.library,
        "api_call_count": u.api_call_count,
        "symbol_count": u.symbol_count,
        "files": u.files,
        "imports": u.imports,
        "kind_counts": u.kind_counts,
        "has_evidence": u.has_evidence,
        "min_confidence": u.min_confidence,
        "max_confidence": u.max_confidence,
    }


## Print analysis results in human-readable format.
#  @param result ProjectAnalysis result object.
def _print_text(result):
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


## Print analysis results in legacy JSON format (backward-compatible).
#
#  Preserves the original dataclasses.__dict__ serialisation and
#  absolute paths, with schema_version added at the root.
#  @param result ProjectAnalysis result object.
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
    output["schema_version"] = result.schema_version  # type: ignore[index]
    print(json.dumps(output, indent=2, ensure_ascii=False))


## Print analysis results in stable JSON format.
#
#  Uses normalized POSIX paths and fixed field order.
#  @param result ProjectAnalysis result object.
def _print_json_stable(result):
    print(json.dumps(_stable_project(result), indent=2, ensure_ascii=False))


## Main entry point for the pcresolve CLI.
def main():
    parser = argparse.ArgumentParser(
        description="Trace API calls in a Python project to their origin libraries."
    )
    parser.add_argument(
        "project_root", nargs="?",
        help="Absolute path to the project root directory."
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results in JSON format (backward-compatible, additive fields)."
    )
    parser.add_argument(
        "--json-stable", action="store_true",
        help="Output results in stable JSON format with normalized paths and fixed field order."
    )
    parser.add_argument(
        "--stdin", action="store_true",
        help="Read project root path from stdin."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print diagnostics in human-readable mode."
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with non-zero code when error diagnostics are present."
    )
    parser.add_argument(
        "--scope-model", choices=("v1", "v2"), default="v1",
        help="Scope model: v1 (legacy single-slot), v2 (lexical scopes). Default: v1."
    )
    parser.add_argument(
        "--usage-summary", action="store_true",
        help="Print aggregated library usage summary in text mode."
    )
    args = parser.parse_args()

    project_root = args.project_root
    if args.stdin:
        project_root = sys.stdin.readline().strip()

    if not project_root:
        parser.print_help()
        sys.exit(1)

    if not os.path.exists(project_root):
        print(f"Error: {project_root} does not exist.", file=sys.stderr)
        sys.exit(1)

    result = analyze_project(project_root, scope_model=args.scope_model)

    if args.json_stable:
        _print_json_stable(result)
    elif args.json:
        _print_json_legacy(result)
    else:
        _print_text(result)
        if args.usage_summary and result.library_usage:
            print("\nLibrary Usage Summary:")
            for lib, u in sorted(result.library_usage.items()):
                print(f"\n{lib}")
                print(f"  files: {len(u.files)}")
                print(f"  api calls: {u.api_call_count}")
                print(f"  symbols: {u.symbol_count}")
                if u.imports:
                    print(f"  imports: {', '.join(u.imports)}")
        if args.verbose and result.diagnostics:
            print("\nDiagnostics:")
            for d in result.diagnostics:
                loc = ""
                if d.lineno:
                    loc = " (L%d:C%d)" % (d.lineno, d.col_offset)
                print("  [%s] %s %s%s: %s" % (d.severity.upper(), d.code, d.file_path, loc, d.message))
            print("\n%d file(s) skipped." % len(result.diagnostics))

    if args.strict:
        for d in result.diagnostics:
            if d.severity == "error":
                sys.exit(1)
