# Experimental value-flow API

The `flow-0.1` contract is experimental. It is separate from the stable
ownership output. `FlowAnalyzer` does not execute analyzed code or import its
dependencies. Existing `analyze_project()` behavior is unchanged.

```python
from pcresolve import FlowAnalyzer, FunctionRef

analyzer = FlowAnalyzer(project_root="/sources/pandas")
entry = FunctionRef(module="pandas.core.tools.datetimes",
                    qualname="to_datetime")
result = analyzer.analyze(entry, max_depth=1)
call = result.find_calls(callee_name="_assemble_from_unit_mappings")[0]
details = result.describe_call_flow(call.id)
expanded = analyzer.expand(result, call.id, additional_depth=1)
payload = expanded.to_dict()
```

Alternatively, supply `source_files=[...]` and `import_roots=[...]`.
Import roots interpret module names; they do not add files. Project input uses
the existing scanner. Inputs record absolute paths and SHA-256 source hashes.
`add_files()` affects subsequent `analyze()` calls. Expansion rejects changed
source sets; rerun analysis after adding or editing files.

## Complete example: pandas 0.21.0 `to_datetime`

This example analyzes the call from `to_datetime` to
`_assemble_from_unit_mappings` in
`pandas/core/tools/datetimes.py`. Use the **v0.21.0** source checkout: other
versions may have different function names, signatures, and control flow.
No pandas installation or pandas runtime dependencies are required. Install
the current PCResolve checkout with `python -m pip install -e .` first.

The questions are:

1. Which entry parameters reach the helper's arguments and formal parameters?
2. Does this particular helper call's result reach an entry return statement?
3. What additional facts become available when the helper body is expanded?

Save the following as `analyze_datetime_flow.py`. The default input is only
`datetimes.py`, which contains both definitions. Pass `--whole-project` to make
the entire checkout available for target and signature resolution.

```python
import argparse
import json
from pathlib import Path

from pcresolve import FlowAnalyzer, FunctionRef


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--whole-project", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("datetime-flow.json"))
    args = parser.parse_args()
    root = args.project_root.resolve()
    source = root / "pandas/core/tools/datetimes.py"
    if not source.is_file():
        parser.error("Expected pandas/core/tools/datetimes.py under project_root")

    if args.whole_project:
        analyzer = FlowAnalyzer(project_root=root)
    else:
        analyzer = FlowAnalyzer(source_files=[source], import_roots=[root])

    entry = FunctionRef(
        module="pandas.core.tools.datetimes",
        qualname="to_datetime",
    )
    initial = analyzer.analyze(
        entry, max_depth=1, max_functions=500, max_call_contexts=2000,
    )
    matches = initial.find_calls(
        caller=entry, callee_name="_assemble_from_unit_mappings",
    )
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one helper call; check the source version and boundaries: "
            + json.dumps(initial.boundaries, ensure_ascii=False)
        )
    call = matches[0]
    details = initial.describe_call_flow(call.id)
    print("Call site:", call.id)
    print("Target:", details["target"])
    print("Parameter bindings:")
    print(json.dumps(details["parameter_bindings"], ensure_ascii=False, indent=2))
    print("Parameter flow roots:", sorted({
        (flow["source_parameter"], flow["target_parameter"], flow["relation"])
        for flow in details["parameter_flows"]
    }))
    print("Helper result -> entry return paths:", len(details["return_flows"]))

    # Enter this exact helper call, not every call from to_datetime.
    expanded = analyzer.expand(initial, call.id, additional_depth=1)
    if call.target is not None:
        print("Collected direct calls inside the helper:")
        for child in expanded.find_calls(caller=call.target):
            print(" ", child.id, child.callee_name)

    # This is a different question: does entry.arg reach entry.return through
    # the available summaries? A found path may bypass the helper entirely.
    parameter_trace = expanded.trace_parameter("arg")
    print("Entry arg -> entry return status:", parameter_trace["status"])
    print("Boundary reasons:", sorted({b["reason"] for b in expanded.boundaries}))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        "initial_call": details,
        "analysis": expanded.to_dict(),
        "entry_parameter_trace": parameter_trace,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved:", args.output.resolve())


if __name__ == "__main__":
    main()
```

Run from a terminal, replacing the checkout path:

```bash
python analyze_datetime_flow.py C:/sources/pandas-0.21.0
python analyze_datetime_flow.py C:/sources/pandas-0.21.0 --whole-project --output results/datetime-flow.json
```

### Interpreting the output

For the single-file v0.21.0 input, the current implementation finds one helper
call with these bindings (unrelated fields omitted):

```json
[
  {"argument": {"position": 0}, "parameter": "arg", "status": "exact"},
  {"argument": {"keyword": "errors"}, "parameter": "errors", "status": "exact"}
]
```

The verified direct parameter-flow roots are `arg -> arg` and
`errors -> errors`. One helper-result-to-entry-return path is retained.
This establishes conditional direct forwarding, not that every execution
reaches the helper or that all possible derived `arg` paths were analyzed.

| JSON field | Meaning in this example |
|------------|-------------------------|
| `initial_call.id` | Exact helper call location; not a function identifier |
| `initial_call.target` | Helper definition, including module, file, and line |
| `parameter_bindings` | Call argument slots mapped to helper formal parameters |
| `parameter_flows` | Entry parameter roots reaching those argument slots |
| `return_flows` | This call's result reaching a return in `to_datetime` |
| `evidence` | Ordered source snippets with file and start/end positions |
| `conditions` | Collected syntactic branch conditions, not feasibility proofs |
| `analysis.functions` | Function summaries actually generated |
| `analysis.inputs` | Available files, source hashes, roots, and initial depth |
| `analysis.boundaries` | Missing targets, cutoffs, and unsupported constructs |
| `entry_parameter_trace` | Composition of entry-parameter-to-entry-return paths |

The distinction between the last two flow queries matters: proving that the
helper's **result** is returned does not prove that the helper's **input** flows
into its result. That requires its body summary. The current helper analysis
is partial and stops at unsupported control flow, so expansion does **not**
collect all calls or all return paths inside it. In particular, do not interpret
the printed child-call list as an exhaustive list from the Python AST.

The example's `trace_parameter("arg")` can report `flow_found` through the
entry's direct `result = arg` branch. This does not establish propagation
through the helper: inspect each path's `call_context` and evidence before
attributing it to the selected call.

### Source scope and further expansion

Both definitions in this example are already available in single-file mode.
For other callees, supplying the project can resolve additional Python
definitions, but cannot remove unsupported-language or external-library
boundaries. Whole-project mode currently parses/indexes available files before
generating reachable flow summaries; it can cost more than single-file mode.

To make additional files available in explicit-file mode:

```python
analyzer.add_files([root / "path/to/additional_definition.py"])
initial = analyzer.analyze(entry, max_depth=1)  # obtain a new snapshot
# Find the call again in initial before expanding it.
```

Replace the placeholder with an actual definition or re-export file. Do not
expand an old snapshot after changing the source set. To expand every available
direct target instead of one selected call, use
`analyzer.analyze(entry, max_depth=2)`. The original `initial` snapshot is not
mutated by `expand`. Each selected expansion currently uses the default budgets
of 500 summaries and 2,000 call sites; it does not inherit custom budgets from
the initial call. `inputs.max_depth` records the initial analysis depth, not
the maximum depth after selected expansions.

For downstream type-change analysis, use these facts to locate candidate
propagation paths, then apply your own type/conversion rules. Value dependence
is not proof of a type change. Missing paths or empty lists are not negative
proofs when boundaries remain. Side effects are outside this version's scope.

## Depth and identity

Depth one summarizes the entry body, including its direct calls and available
callee signatures. Depth two also summarizes their bodies. `expand` starts at
the selected call target and analyzes the requested number of layers below it.
Function summaries are shared; call-result substitution retains call-site
identity. Call IDs are file/line/column locations, stable only for unchanged
source snapshots. Function selectors may include a definition line to resolve
duplicate definitions.

## Facts

Each call provides its caller, syntactic spelling, resolved target when known,
argument-to-parameter bindings, argument sources, parameter flows, and result
flows to the caller's return statements. Defaults are separate bindings, not
fabricated arguments. Return summaries retain parameter and call-result roots.
`trace_parameter(name)` composes expanded parameter-to-return summaries and
returns evidence paths with exact call contexts. It never assumes every input
of an opaque call flows to its output.

Evidence contains source snippets and start/end positions. Conditional branches
are recorded as condition references. Relations distinguish direct transfer,
derived values, and container inclusion. Conditions are syntactic evidence,
not runtime path-feasibility proofs. A found path does not promise execution.

## Current supported subset and boundaries

This first implementation supports named functions, explicit imports and simple
re-exports, positional/keyword/default binding, parameter aliases, expressions,
ordinary assignments, if/else merges, explicit returns, and bounded cross-call
return substitution. Rebound callable variables and decorated targets are not
resolved to a guessed definition. Dynamic argument unpacking is left unresolved.

Loops, try/with, comprehensions, destructuring/heap writes, closures with captured
value substitution, method receiver binding, and dynamic dispatch are not yet
complete. Unsupported statements stop that path and produce a boundary; this
can leave only a partial function summary. C/Cython and external implementation
boundaries remain unresolved. Objects passed into calls may be mutated; heap
effects are not modeled. In particular, discarded results do not prove absence
of side effects. Recursion records a boundary rather than unrolling forever.

Missing targets, unsupported constructs, depth limits, and budget cutoffs are
explicit `boundaries`. `trace_parameter()` returns `unknown` when no path is
found, rather than claiming a negative proof. Consumers must not prune unknown
edges as no-flow. The initial budgets bound distinct summaries and collected
call sites, not the number of all possible runtime contexts. Complete path
enumeration and a public selected-chain query are not provided yet.

Ownership can later consume verified flow evidence, but value dependence alone
does not imply owner preservation (for example, conversion through `str`).
