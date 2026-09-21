# PCResolve Validation

PCResolve validates stable call-site ownership and experimental value flow
separately. The two suites answer different questions and their results must
not be combined into one accuracy score.

## Ownership evaluation

The ownership corpus contains every Python call expression found in 42 locked
real-world projects. Each of the 5,788 records has a reviewed primary owner:
an import-backed library name, `python`, `local`, or `unknown`.

| Metric | Result |
|---|---:|
| Projects | 42 |
| Ground-truth records | 5,788 |
| Primary hits | 5,548 |
| Primary misses | 240 |
| Primary recall | 0.959 |
| AST call coverage | 100% |

Canonical labels live in `ground_truth/calls/`. Review views live in
`ground_truth/review/`, and independently reviewed static boundaries live in
`ground_truth/verification/`. The complete record schema and labeling rules are
documented in the [ground-truth specification](../ground_truth/README.md).

The 240 misses remain in the denominator. They have reviewed
`accepted_unknown` dispositions where project source does not establish the
runtime owner under PCResolve's pure-static contract. A runtime probe can
confirm the true owner, but it does not by itself prove that the owner is
statically recoverable. PCResolve does not add name-based or library-specific
guesses to improve the score.

Run the ownership gates from the repository root:

```bash
python scripts/evaluate_ground_truth.py --view all
python scripts/verify_ground_truth_calls.py --coverage-only
python scripts/add_verification_levels.py --check
python scripts/refresh_ground_truth_snapshots.py --all --check
python scripts/classify_ground_truth_failures.py --release-check
```

## Value-flow regression matrix

The value-flow matrix contains 83 entry functions and 472 reviewed checks.
All checks currently match their expectations.

| Dimension | Checks | Result |
|---|---:|---|
| Lexical call inventory | 82 | 82 matched |
| Selected call presence | 41 | 41 matched |
| Call target | 39 | 39 matched |
| Actual/formal binding | 54 | 54 matched |
| Explicit parameter flow | 65 | 45 positive paths found; 20 negative probes reported no path |
| Implicit receiver flow | 7 | 5 positive paths found; 2 negative probes reported no path |
| Call return to entry return | 41 | 34 positive paths found; 7 negative probes reported no path |
| Entry parameter to entry return | 137 | 75 positive paths found; 62 negative probes reported no path |
| Boundary contract | 6 | 6 matched |

The cases cover argument binding, control flow, containers, analysis budgets,
and four reviewed CPython standard-library function fragments. Expectations
and semantic rationales live with each fixture in
`tests/fixtures/value_flow_matrix/**/manifest.json`.

This is a development regression matrix, not a held-out estimate of
real-project accuracy. `negative_no_path` means that a selected negative probe
did not produce a path; it is not a proof that no runtime dependency exists.
Unresolved bindings, analysis exceptions, and boundary mismatches remain
explicit outcomes and cannot receive negative-test credit.

Run the value-flow gates with:

```bash
python scripts/evaluate_value_flow_matrix.py --strict
python scripts/evaluate_value_flow_matrix.py --output matrix.json --markdown matrix.md
python -m pytest -q tests/test_value_flow_matrix.py tests/test_value_flow_matrix_runner.py tests/test_value_flow_contract.py
```

The generated JSON and Markdown reports include the Git revision, Python
version, analyzer/evaluator hashes, fixture hashes, every declared check, and
diagnostic boundary counts. They are reproducible build artifacts rather than
maintained documentation.

## Interpretation boundary

- Ownership measures primary call-site classification; it does not score every
  symbol-provenance fact.
- Value-flow checks dependency relationships and boundary behavior; it does not
  change ownership classifications or the stable ownership schema.
- Dynamic dispatch, reflection, monkey patching, external implementations,
  arbitrary heap behavior, and budget cutoffs can leave either analysis
  incomplete.
- Missing evidence is reported conservatively. It must not be interpreted as
  proof that an owner or dependency does not exist at runtime.
