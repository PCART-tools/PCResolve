## @package pcresolve.cli
#  Provide command-line entry point for the pcresolve tool.
#
#  Usage:
#    pcresolve /path/to/project
#    pcresolve --json /path/to/project
#    python -m pcresolve /path/to/project
#    echo /path/to/project | pcresolve --stdin

import argparse
import json
import os
import sys
from .cross_file import analyze_project


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
                chain_str = " -> ".join(chain)
                print(f"  {symbol}: {chain_str}")

    print("\nAll API calls:")
    for f in result.files:
        if f.api_calls:
            print(f"\n{f.module_name} module:")
            for call in f.api_calls:
                print(f"  {call.expression} -> {call.top_library}")


## Print analysis results in JSON format.
#  @param result ProjectAnalysis result object.
def _print_json(result):
    def _serialize(obj):
        if hasattr(obj, '__dataclass_fields__'):
            return {k: _serialize(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [_serialize(v) for v in obj]
        else:
            return obj

    print(json.dumps(_serialize(result), indent=2, ensure_ascii=False))


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
        help="Output results in JSON format."
    )
    parser.add_argument(
        "--stdin", action="store_true",
        help="Read project root path from stdin."
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

    result = analyze_project(project_root)

    if args.json:
        _print_json(result)
    else:
        _print_text(result)
