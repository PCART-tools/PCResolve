# Experimental value-flow API

The `flow-0.2` contract is experimental. It is separate from the stable
ownership output. `FlowAnalyzer` does not execute analyzed code or import its
dependencies. Existing `analyze_project()` behavior is unchanged.

`flow-0.2` gives call IDs a complete source range, adds end positions and
effect records to calls, records element paths for variadic bindings, marks
generator summaries, and records trusted parameter-shape inputs. Consumers of
`flow-0.1` call IDs must rediscover calls with `find_calls()` after upgrading.

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
| `initial_call.id` | Opaque call-site identifier using the complete source range; not a function identifier |
| `initial_call.target` | Helper definition, including module, file, and line |
| `parameter_bindings` | Call argument slots mapped to helper formal parameters |
| `parameter_flows` | Entry parameter roots reaching those argument slots |
| `argument_flows` | All tracked roots reaching argument slots, including other call results |
| `capture_bindings` | Call-time bindings of enclosing variables read by a nested function |
| `return_flows` | This call's result reaching a return in `to_datetime` |
| `effects` | Exact supported writes through parameters or nonlocal captures |
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
proofs when boundaries remain. Inspect `effects` and `mutation_flows` before
following a mutable value across a resolved call.

## Depth and identity

Depth one summarizes the entry body, including its direct calls and available
callee signatures. Depth two also summarizes their bodies. `expand` starts at
the selected call target and analyzes the requested number of layers below it.
Function summaries are shared; call-result substitution retains call-site
identity. Call IDs are opaque identifiers built from the complete source range
and are stable only for unchanged source snapshots. Function selectors may
include a definition line to resolve
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
Undecorated same-class methods on the unchanged first receiver parameter or its
direct aliases can be
expanded as `lexical_method_candidate` targets, with an implicit receiver binding
in `argument_sources`. `dynamic_method_override_possible` remains explicit:
these are conditional lexical candidates, not guaranteed runtime dispatch.

Unshadowed builtin `staticmethod` and `classmethod` decorators use their Python
descriptor binding rules. A nominal zero-argument `super()` call can resolve a
method on one statically available base. A simple local decorator that accepts
one function and returns one nested callable can resolve to that replacement.
Other descriptors, multiple inheritance, decorator factories, and dynamic
replacement remain boundaries.

Conditional expressions preserve the two value branches separately from their
test. Tuple/list destructuring records element projections; matching literal
tuple/list assignments preserve individual elements. General projections still
represent a dependency on the aggregate, not a fully resolved element type.

For/while loops compute a bounded may-flow fixed point, including break/continue
and loop else handling. Loop entry sources join normal/continue back edges until
abstract dependencies stabilize, with a maximum of 16 passes. Function summaries
include `loops` records with iterations and `converged`/`bounded` status.
Non-convergence produces `loop_iteration_limit`. One witness is retained per
dependency; this does not enumerate iteration counts or prove feasibility.
Repeated evaluation of a call site does not spend the call budget repeatedly.
Known local list/dict/set protocols include bounded `append`, `clear`, `get`,
and list `pop` behavior. Resolved, straight-line callees can expose exact
`append`, `clear`, and `nonlocal` write effects. Other heap effects remain
explicit boundaries or unknown behavior.

One-argument unshadowed `str`, `repr`, `bool`, `len`, `list`, `tuple`, and `set`
calls carry a builtin derived-result dependency. This is input dependence, not
identity or owner preservation. Arbitrary receiver methods do not inherit this
rule; external return contracts remain opt-in.

This implementation supports named functions, direct lambda values, local
callable aliases, explicit imports and simple
re-exports, positional/keyword/default binding, parameter aliases, expressions,
ordinary assignments, if/else merges, try/except/else/finally, explicit returns,
lexically nested definitions, direct closure bindings, definition-time nested
defaults, literal argument expansion, path-sensitive variadic captures, and
bounded cross-call return substitution. Builtin static/class descriptors,
nominal zero-argument `super()`, and a narrow statically returned replacement
decorator are resolved when their definitions are unambiguous. Unknown dynamic
argument expansion remains a `dynamic_argument_expansion` boundary while
independent explicit keyword bindings are retained.

Unbounded loop reasoning, `with`, starred destructuring/heap writes, escaping
closures, general receiver binding, multiple inheritance, and dynamic dispatch are not yet
complete. Unsupported statements stop that path and produce a boundary; this
can leave only a partial function summary. C/Cython and external implementation
boundaries remain unresolved. Effects outside the exact local summaries remain
unknown; discarded results therefore do not prove absence of side effects.
Recursion records a boundary rather than unrolling forever.

Missing targets, unsupported constructs, depth limits, and budget cutoffs are
explicit `boundaries`. `trace_parameter()` returns `unknown` when no path is
found, rather than claiming a negative proof. Consumers must not prune unknown
edges as no-flow. The initial budgets bound distinct summaries and collected
call sites, not the number of all possible runtime contexts. Complete path
enumeration and a public selected-chain query are not provided yet.

Ownership can later consume verified flow evidence, but value dependence alone
does not imply owner preservation (for example, conversion through `str`).

## Exception paths and nested functions

### Guarded string receivers and evidence performance

Within a positive, unshadowed `isinstance(value, str)` branch, direct name
receivers support a derived receiver-to-result dependency for `split`, `rsplit`,
`strip`, `lstrip`, `rstrip`, `startswith`, and `endswith`. The target is marked
`python_protocol`; `string_subclass_override_possible` records that an
overriding subclass method is not ruled out. This is a conditional builtin
implementation summary, not exact runtime dispatch. Reassignment discards the
old refinement and derived operations do not automatically retain it. Unknown
receivers do not receive contracts just because their method names match.

`partition` and `rpartition` receive a three-slot result contract when the
receiver has a guarded or trusted `str` shape. Each output slot derives from the
receiver. Syntax such as three-target unpacking does not itself establish the
receiver type, so the same call on an unconstrained parameter remains unresolved.

Resolved generator functions summarize `yield`/`yield from` values as iterator
elements. The unshadowed one-argument `next()` protocol projects one such
element. Creating a generator does not apply its body effects; scheduling and
general iterator state are outside this summary.

Evidence extraction indexes UTF-8 source lines and caches snippets by source
span. AST column offsets are byte offsets, including for Unicode identifiers.
It no longer rescans the entire module for each piece of evidence. Deep expansion
can still cost substantially more than depth one; call budgets and iteration
limits remain relevant, and terminal rendering of large evidence output can add
latency. Use `--json --output result.json` to avoid terminal rendering costs.

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

## Constructor fields, containers, and recursive return queries

A direct constructor assignment such as `self.mapper = Mapper()` can supply a
candidate for `self.mapper.resolve(...)`. The current rule requires a unique
field write, a direct top-level assignment in an undecorated `__init__`, and an
available class and method definition. Conflicting writes and known dynamic
attribute hooks reject the candidate. Calls expose
`target_status="constructor_field_candidate"` and a
`constructor_field_assumption` boundary with assignment evidence. This is
conditional on normal initialization and dispatch; it does not prove the runtime
class of every possible receiver. Existing dynamic dispatch boundaries remain.

Local literal containers have allocation identities, so aliases share modeled
contents. Supported effects include list `append`/`pop`, container `clear`,
dictionary item assignment/unpacking, and dictionary `get`. Dictionary keys are
part of whole-container results but excluded from value lookup; later exact-key
writes mask matching wildcard paths. `mutation_flows` records appended value
dependencies separately from the call's return: `append` returns `None`.
An unambiguous clear removes content dependencies; an ambiguous receiver uses a
weak update. Known dictionary keys select matching values and suppress a default
only when the key is known to be present. Unsupported local container methods
report `container_effect_unknown`. Exact straight-line local callees can apply
parameter-based append/clear effects and direct `nonlocal` assignments. This is
not a general heap or alias analysis: arbitrary nested mutable objects, escaping
aliases, conditional effects, and other callee side effects are not fully modeled.

Conditional expressions merge the possible container effects of both branches;
short-circuit expressions preserve the effects of evaluated prefixes. A pending
return retains the local container identity through `finally`: appending or
clearing changes its returned contents, while rebinding the local variable does
not replace the previously selected return object. Dictionary `get` retains a
call-result endpoint and exposes its selected receiver/default dependencies in
`return_dependencies`.

Return dependencies can carry `output_path` (the containing result element) and
`projection` (the selected input element). These preserve selections through
expanded calls. For example, if `pair(x, y)` returns `(x, y)`, then
`a, b = pair(x, y); return b` carries `y` to the return without also carrying `x`.
Unknown indices remain conservative; general sequence operations and shape
inference are not complete. Literal string `join` consumes iterable element
dependencies. Positive string guards in short-circuit `and` expressions can
refine subsequent operands.

`trace_parameter()` computes return dependencies over the functions already
present in the snapshot using a bounded fixed point. This supports recursive
parameter permutation and nested return selection; it does not expand additional
source functions. Query results include `summary_status` (`converged` or
`bounded`) and `summary_iterations`. The solver retains one evidence witness per
abstract dependency, with limits of 32 iterations and 2,048 dependencies per
summary. Recursive container nesting can keep growing and reach these limits.
In that case the query adds `return_summary_limit` to its own boundaries without
mutating the analysis snapshot. `converged` means convergence of the modeled
dependencies, not completeness of Python semantics or exhaustive path evidence.
An empty result remains `unknown`, not a proof of no flow.

For the repository example:

```python
analysis = FlowAnalyzer(project_root="src").analyze(
    FunctionRef(module="pcresolve.cross_file",
                qualname="ProjectAnalyzer.trace_symbol"),
    max_depth=1,
)
for call in analysis.find_calls(
        callee_name="self.module_mapper.resolve_module_name"):
    print(call.target, call.target_status)
for call in analysis.find_calls(callee_name="tops.append"):
    print(call.mutation_flows)
query = analysis.trace_parameter("symbol")
print(query["summary_status"], query["return_paths"], query["boundaries"])
```

Boundary counts depend on revision, expansion budgets, and available sources.
Successful builtin/local container protocol classifications are not themselves
boundaries; genuine assumptions and truncations remain visible. Identical
boundary records are deduplicated. More than one distinct boundary may still
refer to a single call. Ownership classification is unchanged by these value-flow
features.

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

## Optional trusted parameter shapes

Source code does not always contain enough information to select a builtin
protocol. A consumer can attach a reviewed shape contract to a defined function:

```python
analyzer = FlowAnalyzer(
    project_root=root,
    parameter_shapes={
        "url_excerpt._splituser": {
            "parameters": {"host": "str"},
            "provenance": "Reviewed CPython _splituser input contract",
        },
    },
)
```

Keys are exact `module.qualname` definitions. Contracts and provenance are
copied into `inputs.parameter_shapes`; affected function summaries expose their
`parameter_shapes`. The current protocol consumer recognizes `str` for the
documented string methods above. Other nonempty shape names are retained for
future consumers without changing value-flow semantics. PCResolve does not
verify the supplied claim. Changing it requires a new analysis snapshot before
expansion.
