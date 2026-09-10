# Independent value-flow probes

This first evaluation set contains 12 manually written synthetic functions in
`tests/fixtures/value_flow_eval`. It is independent of `trace_symbol` and the
existing implementation fixtures, but is **not** a held-out real-project study
or a representative accuracy estimate. Once used to guide fixes, it becomes a
development regression set; future generalization claims need fresh cases.

The expected manifest was written before running the initial evaluation. No
analyzer code was changed before recording that baseline. Expectations describe explicit value
dependencies on normal executions of the fixture implementations, excluding
monkey-patching and subclass overrides. Control-only dependencies are excluded.
Negative labels are derived by inspecting these small bodies, not by asking the
analyzer for an answer. The manifest should receive independent human review.

Run from the repository root with the package installed:

```shell
python scripts/evaluate_value_flow.py --output evaluation.json
python -m pytest tests/test_value_flow_evaluation.py -q
```

The runner uses all Python files in the fixture directory and depth 3. It checks
five dimensions separately: call target, actual/formal binding, parameter-to-call
flow, call-result-to-entry-return flow, and composed entry-parameter-to-return
flow. The first four currently cover only three simple direct-call cases; these
small successes do not establish method dispatch or advanced binding accuracy.

Positive absence is `positive_missing`, not proof of no flow. Negative absence is
`negative_no_path`, not a proven negative. An unexpected reported dependency is
`negative_flow_reported`. Query convergence and boundary reason counts remain in
the report. No overall accuracy score hides these distinctions. Tests check report
integrity and now protect the repaired probes as regressions. The original
expectations and baseline remain unchanged.

## Baseline at analyzer commit 59f82e7

The complete baseline is in `value-flow-evaluation-baseline.json`.

| Dimension | Observations |
|---|---|
| Targets | 3/3 matched |
| Actual/formal bindings | 4/4 matched |
| Parameter-to-call flow | 4 positive paths found; 3 negative probes had no path |
| Call-result-to-return flow | 1 positive path found; 2 negative probes had no path |
| Entry-parameter-to-return flow | 5/10 positive paths found; 2/7 negative probes reported a flow |

Missing positives cover keyword unpacking, comprehensions, nested mutable aliases,
callee mutation of a caller's container, and inherited method dispatch. Unexpected
flows occur for the excluded first element in negative indexing and slicing.
These are implementation gaps, not evidence of reaching a static-analysis limit.

## After probe-driven fixes

`value-flow-evaluation-current.json` records 10/10 positive return dependencies
found and 7/7 negative probes without a reported path. Other dimensions retain
their baseline results. This is a development-set result, not held-out accuracy.
Additional counterexamples test reverse slices, out-of-range indices, append
followed by indexing, comprehension scope and empty results, nested alias clear
and rebinding, and class attributes that shadow inherited methods.

The implementation scope is deliberately explicit:

- Constant negative indices and slices use known local list/tuple positions;
  unknown lengths and indices remain conservative.
- Literal `**` dictionaries with unique constant string keys can bind keywords;
  general runtime mappings remain an expansion boundary.
- Synchronous list/set/dict comprehensions propagate element dependencies in a
  separate local scope. Arbitrary filter feasibility and asynchronous/generator
  execution are not fully modeled.
- Literal nested containers preserve references until materialization. General
  escaping objects and arbitrary heap mutation remain outside this model.
- A body consisting of one unconditional `formal.append(other_formal)` statement
  in a synchronous function supplies an append effect for a known local list argument. This small summary
  is read from the indexed definition even when body expansion is depth-limited;
  it does not imply general interprocedural effect analysis.
- Available methods in a simple single-base chain can be candidates. Decorators,
  dynamic attribute hooks, multiple bases, and detected attribute shadowing block
  this fallback. Dynamic override assumptions remain explicit boundaries.

Next evaluation work should add manually reviewed, revision-pinned real functions
from unrelated projects, including positive and negative edges. Keep development
and held-out groups distinct, freeze the latter before evaluating a new version,
and report unsupported constructs, conditional dispatch assumptions, and budget
truncations separately. Do not use declining boundary counts as an accuracy score.
