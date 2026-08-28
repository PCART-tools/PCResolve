# PCResolve 1.0.5 Ground Truth Failure Analysis

Snapshot: 2026-08-28

## Executive Summary

The locked evaluation set contains 5,788 call records across 42 projects.
PCResolve currently produces 5,546 primary hits and 242 primary mismatches,
for recall 0.958. AST call coverage is complete at 5,788/5,788. There are no
missing, stale, or uncovered call predictions.

The remaining records are ownership-classification mismatches. They do not
all represent sound implementation targets. Ground truth records the semantic
or runtime callable owner, while release disposition asks whether project
source proves that owner under a pure-static contract.

The generated [failure disposition report](failure-dispositions.md) currently
places 179 records in the 1.0.5 repair queue and accepts 63 `unknown` results
as static-analysis boundaries. Accepted boundaries remain scored misses so
the evaluation does not hide unavailable runtime information.

## Static Evidence Boundary

PCResolve may select an exact owner when project source provides convergent
evidence through imports, lexical assignments, local returns, constructor
bindings, container elements, or project call edges. It must retain
`unknown` when the exact owner depends only on one of these conditions:

- an uncalled function parameter or unreachable code
- dynamic dispatch with no statically enumerable target
- a callback invoked only by an external framework
- the result type or iteration protocol of an external library API
- conflicting project call sites that do not converge on one owner

Runtime probes validate ground-truth labels, but probe results do not become
hardcoded library or method mappings in the analyzer.

## Current Analyzer Outcomes

| Current reason | Records | Share | Meaning |
|---|---:|---:|---|
| `UNRESOLVED` | 219 | 90.5% | The analyzer preserves uncertainty at a receiver, return, attribute, item, or call edge. |
| `LOCAL_DEFINITION` | 13 | 5.4% | A local binding is selected although the reviewed runtime callable has another owner. |
| `TRANSITIVE_IMPORT` | 6 | 2.5% | Producer or enclosing-object provenance leaks into the callable owner. |
| `FLOW_MERGE` | 4 | 1.7% | Multiple static paths do not converge on the reviewed owner. |
| **Total** | **242** | **100.0%** | |

## Expected Owner Kind

| Expected kind | Records | Share |
|---|---:|---:|
| `library` | 150 | 62.0% |
| `python` | 85 | 35.1% |
| `local` | 7 | 2.9% |
| **Total** | **242** | **100.0%** |

## Highest Impact Families

| Failure family | Records |
|---|---:|
| General transitive receiver methods | 50 |
| Python protocol methods | 46 |
| NumPy array receivers | 28 |
| Torch tensor receivers | 26 |
| Python string methods | 17 |
| Matplotlib receivers | 11 |
| Library result boundaries | 9 |
| Conversion boundaries | 9 |
| Pandas receivers | 8 |
| Pandas receiver chains | 5 |

## Release Disposition

| Disposition | Records | Meaning |
|---|---:|---|
| `fix_1_0_5` | 179 | Candidate repair supported by the current evidence taxonomy. |
| `accepted_unknown` | 63 | Runtime owner is known, but project source does not prove it. |
| `ground_truth_correction` | 0 | No canonical GT correction is currently pending. |
| **Total** | **242** | |

The repair queue is further divided into 94 bounded receiver-flow records,
76 same-scope result or protocol records, eight conservative-identity
records, and one local-identity record. Before implementation, each group
must be checked for actual project call evidence. A category label alone is
not sufficient proof that its exact owner is statically recoverable.

## Current Repair Direction

1. Continue context-sensitive propagation only where all relevant project
   call edges converge.
2. Preserve structured parameter, subscript, tuple, and return sources across
   local calls without promoting a producer to its result object.
3. Reclassify dead-code and external-entry cases as accepted boundaries when
   project source contains no owner evidence.
4. Prefer an honest `unknown` over a library-name, method-name, or result-type
   guess.
5. Keep changes grouped by repair theme and amend follow-up corrections into
   that theme before review.

## Release Validation

Every repair batch must preserve these checks:

```bash
python -m pytest -q
python scripts/add_verification_levels.py --check
python scripts/verify_ground_truth_calls.py --coverage-only
python scripts/refresh_ground_truth_snapshots.py --all --check
python scripts/evaluate_ground_truth.py --view all
python scripts/classify_ground_truth_failures.py --check
```

The release target is not merely a higher aggregate recall. Every reduction
must correspond to a reviewed source-supported owner, keep call coverage
complete, preserve zero illegal keys, and avoid replacing `unknown` with an
unsupported guess.
