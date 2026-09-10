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

### Command line

Analyze the entry's direct calls using the whole checkout as available source:

```bash
pcresolve C:/sources/pandas-0.21.0 --value-flow --entry pandas.core.tools.datetimes:to_datetime --depth 1
```

Write the complete experimental flow JSON to a UTF-8 file:

```bash
pcresolve C:/sources/pandas-0.21.0 --value-flow --entry pandas.core.tools.datetimes:to_datetime --depth 1 --json --output datetime-flow.json
```

Limit available source to the single definition file:

```bash
pcresolve --value-flow --source-file C:/sources/pandas-0.21.0/pandas/core/tools/datetimes.py --import-root C:/sources/pandas-0.21.0 --entry pandas.core.tools.datetimes:to_datetime --depth 1 --json --output datetime-flow.json
```

`python -m pcresolve` is equivalent to `pcresolve`. Paths are relative to the
current working directory unless absolute. Use either the positional project
directory or repeated `--source-file` options, not both. `--import-root` is
repeatable and controls module naming only. With explicit files and no import
root, module names default to each file's basename.

| Option | Meaning |
|--------|---------|
| `--value-flow` | Select experimental flow analysis instead of ownership |
| `--entry MODULE:QUALNAME` | Required entry; nested qualnames use dots |
| `--depth N` | Call-edge depth, default 1 |
| `--max-functions N` | Distinct function summary budget, default 500 |
| `--max-call-contexts N` | Collected call-site budget, default 2000 |
| `--json` | Emit `FlowAnalysis.to_dict()`, including evidence and boundaries |
| `--output PATH` | Write the selected text/JSON format to a UTF-8 file instead of stdout |

Output files are overwritten; their parent directory must already exist.
Without `--json`, the CLI prints per-call parameter flows, return-flow evidence,
and boundaries. Empty flow lists are not proofs of absence. A successful partial
analysis exits 0; invalid arguments, missing explicit files, unresolved entry
selection, and output errors exit 2. Individual parse failures remain recorded
analysis boundaries when the entry can still be analyzed.

`--stdin` can supply the project directory. Ownership-specific display and
explain options are not supported in flow mode. Existing commands without
`--value-flow` keep their ownership output. Selected incremental expansion,
trusted return summaries, and composed parameter queries currently use the
Python API; the CLI performs a single analysis at the requested depth.

### Python API

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

The verified parameter-flow roots are `arg -> arg` (direct and derived) and
`errors -> errors` (direct). The origin-adjustment try blocks now preserve
derived dependencies. One helper-result-to-entry-return path is retained.
This establishes conditional dependencies, not that every execution reaches
the helper or that all possible runtime paths are feasible.

| JSON field | Meaning in this example |
|------------|-------------------------|
| `initial_call.id` | Exact helper call location; not a function identifier |
| `initial_call.target` | Helper definition, including module, file, and line |
| `parameter_bindings` | Call argument slots mapped to helper formal parameters |
| `parameter_flows` | Entry parameter roots reaching those argument slots |
| `argument_flows` | All tracked roots reaching argument slots, including other call results |
| `capture_bindings` | Call-time bindings of enclosing variables read by a nested function |
| `return_flows` | This call's result reaching a return in `to_datetime` |
| `evidence` | Ordered source snippets with file and start/end positions |
| `conditions` | Collected syntactic branch conditions, not feasibility proofs |
| `analysis.functions` | Function summaries actually generated |
| `analysis.inputs` | Available files, source hashes, roots, and initial depth |
| `analysis.boundaries` | Missing targets, cutoffs, and unsupported constructs |
| `entry_parameter_trace` | Composition of entry-parameter-to-entry-return paths |

The distinction between the last two flow queries matters: proving that the
helper's **result** is returned does not prove that the helper's **input** flows
into its result. That requires its body summary or an explicit trusted contract.
The four `_convert_listlike` calls now resolve to the nested function, with
separate explicit-argument and closure bindings. The `Series` call exposes the
inner call result in `argument_flows` for position 0; this alone does not prove
that `Series` preserves that input in its result. The helper analysis remains
partial at unsupported constructs such as loops, so expansion does **not**
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

The analyzer now separates syntactic call coverage from flow evaluation.
Calls behind unsupported statements or unreachable exits are retained with
`analysis_status="not_analyzed"`; they do not claim executable flow paths.
Collection remains subject to the call-site budget. `target_status` and
boundary records distinguish `builtin_boundary`, `receiver_unresolved`,
`flow_not_analyzed`, and missing definitions. Boundaries include callee spelling.

`receiver_sources` records method receivers independently of explicit arguments.
Undecorated same-class methods on the unchanged first receiver parameter can be
expanded as `lexical_method_candidate` targets, with an implicit receiver binding
in `argument_sources`. `dynamic_method_override_possible` remains explicit:
these are conditional lexical candidates, not guaranteed runtime dispatch.

Conditional expressions preserve the two value branches separately from their
test. Tuple/list destructuring records element projections; matching literal
tuple/list assignments preserve individual elements. General projections still
represent a dependency on the aggregate, not a fully resolved element type.

For/while loops use a bounded zero/one-iteration approximation with
`loop_approximation` boundaries, including break/continue and loop else handling.
This exposes iterable dependencies and calls but does not solve loop-carried
dependencies to a fixed point or prove feasibility. Unknown methods such as
`append` still have no heap-effect summary.

One-argument unshadowed `str`, `repr`, `bool`, `len`, `list`, `tuple`, and `set`
calls carry a builtin derived-result dependency. This is input dependence, not
identity or owner preservation. Arbitrary receiver methods do not inherit this
rule; external return contracts remain opt-in.

This first implementation supports named functions, explicit imports and simple
re-exports, positional/keyword/default binding, parameter aliases, expressions,
ordinary assignments, if/else merges, try/except/else/finally, explicit returns,
lexically nested definitions, direct closure bindings, definition-time nested
defaults, and bounded cross-call return substitution. Rebound callable variables and decorated targets are not
resolved to a guessed definition. Dynamic argument unpacking is left unresolved.

Loop fixed points, with, comprehensions, starred destructuring/heap writes, escaping closures,
nonlocal mutation, general receiver binding, and dynamic dispatch are not yet
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

## Exception paths and nested functions

Normal completion of `try` enters `else`; raised exits are dispatched to possible
handlers. Potential expression exceptions retain the environment before the
statement, rather than using the final environment of the entire try body.
Explicit known exception names exclude unrelated known builtin handlers;
unknown exception types and custom inheritance are conservatively considered.
This is not a complete exception-type system. `finally` executes over pending
normal, return, and exceptional exits. A return or raise in finally replaces
the pending exit; an ordinary assignment does not change a previously evaluated
return value.

Nested functions are resolved in lexical order. Their free variables use
`capture_bindings`, separate from formal arguments. Captures use the available
call-time environment; nested defaults are captured at definition time. These
facts support direct local invocation, not arbitrary escaping closure objects.

## Optional trusted return summaries

Opaque calls are not assumed to forward their arguments. A consumer can opt in
to a documented return dependency when it has independently verified one:

```python
analyzer = FlowAnalyzer(
    project_root=root,
    return_summaries={
        "vendor.wrap": {
            "parameters": ["data"],
            "returns": [{"parameter": "data", "relation": "contained"}],
            "provenance": "Consumer-verified vendor.wrap contract, version 1",
        },
    },
)
```

This is an illustrative contract, not a bundled rule for any actual library.
Keys are exact module-qualified imported callable names. The initial contract
format describes ordered positional-or-keyword parameters; advanced signatures
are not supported by this format. A contract is used only when a concrete body
target is unavailable and the callable has not been rebound. A resolved body
takes precedence. Relations are `direct`, `derived`, or `contained`; combining
paths preserves containment unless a derived operation is present.

Contracts are copied into `inputs.return_summaries`, and each dependency carries
the supplied provenance in its evidence. PCResolve does not verify these claims.
`return_dependencies` on the call exposes the applied contract. Missing body
definitions remain boundaries even when such a contract supplies a return
dependency; a contract does not make the implementation available for expansion.
Changing contracts requires a new `analyze()` snapshot before expansion.
