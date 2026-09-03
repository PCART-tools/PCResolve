# PCResolve 1.0.5 Ground Truth Failure Analysis

Snapshot: 2026-09-03

## Executive Summary

The locked evaluation set contains 5,788 call records across 42 projects.
PCResolve produces 5,548 primary hits and 240 primary mismatches, for recall
0.959. AST call coverage is complete at 5,788/5,788. There are no missing,
stale, or uncovered call predictions.

All 240 mismatches have an `accepted_unknown` release disposition. There are
zero `fix_1_0_5` records and zero pending ground-truth corrections. Accepted
unknowns remain scored misses so the evaluation continues to expose the
limits of project-source-only analysis.

The generated [failure disposition report](failure-dispositions.md) is the
authoritative record for every mismatch and its source-backed justification.

## Static Evidence Boundary

PCResolve may select an exact owner when project source provides convergent
evidence through imports, lexical assignments, local returns, constructor
bindings, container elements, or project call edges. It retains `unknown`
when the exact owner depends only on conditions such as:

- a parameter whose function has no project-source call site or is dead code;
- dynamic dispatch with no statically enumerable target;
- a callback invoked only by an external framework;
- the result type or iteration protocol of an external library API;
- conflicting project call sites that do not converge on one owner.

Runtime probes validate ground-truth ownership. They do not become hardcoded
library, method, or return-type mappings in the analyzer.

## Current Analyzer Outcomes

| Current reason | Records | Share | Meaning |
|---|---:|---:|---|
| `UNRESOLVED` | 235 | 97.9% | Project source does not establish one exact owner. |
| `FLOW_MERGE` | 5 | 2.1% | Multiple static paths do not converge on one owner. |
| **Total** | **240** | **100.0%** | |

## Expected Owner Kind

| Expected kind | Records | Share |
|---|---:|---:|
| `library` | 155 | 64.6% |
| `python` | 84 | 35.0% |
| `local` | 1 | 0.4% |
| **Total** | **240** | **100.0%** |

## Highest Impact Families

| Failure family | Records |
|---|---:|
| General transitive receiver methods | 54 |
| Python protocol methods | 44 |
| NumPy array receivers | 26 |
| Torch tensor receivers | 26 |
| Python string methods | 19 |
| Pandas receivers | 11 |
| Matplotlib receivers | 11 |
| Library result boundaries | 9 |
| Conversion boundaries | 9 |

## Review Evidence

| Verification level | Records | Role |
|---|---:|---|
| `static_context` | 175 | Source context proves the GT owner and the static evidence boundary. |
| `dynamic_probe` | 62 | Runtime inspection confirms the GT owner; source review separately justifies `unknown`. |
| `manual_reasoned` | 3 | Manual semantic review establishes the GT label and boundary. |
| **Total** | **240** | |

Each accepted boundary is tied to exact GT call identities and a digest of the
project's Python sources in `static-boundary-reviews.json`. Source, location,
expected-owner, or analyzer-outcome drift invalidates the review.

## Release Disposition

| Disposition | Records | Meaning |
|---|---:|---|
| `fix_1_0_5` | 0 | No source-supported analyzer repair remains open. |
| `accepted_unknown` | 240 | The exact runtime owner is not established by project source. |
| `ground_truth_correction` | 0 | No canonical GT correction remains open. |
| **Total** | **240** | |

## Release Validation

```bash
python -m pytest -q
python scripts/add_verification_levels.py --check
python scripts/verify_ground_truth_calls.py --coverage-only
python scripts/refresh_ground_truth_snapshots.py --all --check
python scripts/evaluate_ground_truth.py --view all
python scripts/classify_ground_truth_failures.py --release-check
```

The release target is evidence-backed classification rather than perfect
runtime reconstruction. Exact owners supported by project source must be
primary hits. Evidence-limited calls remain explicit `unknown` results and
visible GT misses. The current snapshot satisfies the stable-release gate.
