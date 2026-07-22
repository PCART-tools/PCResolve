# PCResolve 1.0.5 Ground Truth Failure Analysis

Snapshot: 2026-07-22, after bounded parameter receiver ownership repair

## Executive Summary

The locked evaluation set contains 5,788 call records across 42 projects.
PCResolve currently produces 5,354 primary hits and 434 primary mismatches,
for recall 0.925. AST coverage is complete at 5,788/5,788, with no missing,
stale, or uncovered call predictions. The remaining failures are ownership
classification failures, not call collection failures.

The previous tracked snapshot contained 5,320 hits and 468 mismatches, for
recall 0.919. Under the corrected current contract, the cross-snapshot audit
finds 37 improved records and zero regressions. The tracked hit count rises by
34 because three AIBO dead-code calls remained hits while their labels were
corrected from `local` to `unknown`.

Five dead-code labels were corrected in total. Three AIBO parameter receivers
and two unreachable EJPLab tensor parameters now use `unknown` because no
executable call site establishes an object owner. These corrections preserve
the rule that names, annotations, and surrounding framework context are not
sufficient ownership evidence.

Four remaining records are the documented `request.json.get(...)` framework
payload boundary. The required 1.0.5 repair queue therefore contains 430
records.

## Parameter Receiver Repair

The current batch adds bounded call-site evidence without claiming a complete
call graph or type system.

| Change | Contract |
|---|---|
| Same-file and cross-file argument convergence | A parameter receiver gets an owner only when all discovered call sites converge. |
| Local constructors and constructor attributes | Project-local class instances remain `local`; imported objects stored in their attributes retain their imported owner. |
| Static callbacks and parameterization | Statically enumerated callback tables and `pytest.mark.parametrize` values can supply bounded argument evidence. |
| Parameter-derived expressions | Subscripts, arithmetic, conflicting call sites, and uncalled parameters remain `unknown`. |
| Explicit method-result ownership | Small reviewed contracts cover result objects such as selected Box2D body constructors without promoting every method result. |
| Local callable protection | Qualified project class constructors resolve to `local` before their module prefix can be mistaken for a library. |

The repair improves records in AIBO, allnews, EJPLab, greenbenchmark,
simulation, and Youtube. The regression comparison reports 37 improvements
and zero prior current-contract hits lost.

Nine existing v1/v2 hard baselines were re-recorded after this audit. The
baseline count remains 21. This records intentional `local` or unsupported
library results becoming `unknown`; it does not waive any locked GT hit.

## Classification By Analyzer Outcome

| Current reason | Records | Share | Failure mechanism |
|---|---:|---:|---|
| `LOCAL_DEFINITION` | 219 | 50.5% | A local binding is still treated as proof that the callable implementation is project-local. |
| `UNRESOLVED` | 173 | 39.9% | Receiver ownership is lost through parameters, returns, branches, attributes, subscripts, or chains. |
| `TRANSITIVE_IMPORT` | 33 | 7.6% | Import provenance of a producer or enclosing object leaks into the callable owner. |
| `RETURN_PROPAGATION` | 7 | 1.6% | A function owner is propagated to a result object with a different callable surface. |
| `FLOW_MERGE` | 2 | 0.5% | Multiple static paths do not converge to the reviewed owner. |
| **Total** | **434** | **100.0%** | |

### Local Definition Overreach

This remains the largest failure group. A receiver name bound in project code
is often resolved to `local`, even when its callable surface belongs to an
import-backed library or Python. Common examples are pandas DataFrames, NumPy
arrays, torch Tensors, regular-expression matches, strings, and containers.

### Unresolved Receiver Loss

These records preserve uncertainty instead of guessing. Common loss points
are local function results, nested attributes, subscript results, chained
calls, and parameter paths for which the bounded call-site model has
insufficient evidence.

### Producer And Result Leakage

`TRANSITIVE_IMPORT` and `RETURN_PROPAGATION` failures still conflate a
producer with its returned object. Remaining examples include argparse
values, XML text, local wrappers, and protocol-bearing library results that
do not yet have a reviewed static contract.

## Classification By Expected Kind

| Expected kind | Records | Share | Typical missing evidence |
|---|---:|---:|---|
| `library` | 267 | 61.5% | Receiver identity through parameters, returns, attributes, conversions, and chains |
| `python` | 145 | 33.4% | String, container, mapping, and Python protocol object identity |
| `unknown` | 16 | 3.7% | Branch-dependent, dead, or unconstrained polymorphic receivers |
| `local` | 6 | 1.4% | Project-local callable identity overwritten by library evidence |
| **Total** | **434** | **100.0%** | |

## Highest Impact Families

| Failure family | Records |
|---|---:|
| General transitive receiver methods | 82 |
| Python protocol methods | 69 |
| NumPy array receivers | 51 |
| Python string methods | 36 |
| Torch tensor receivers | 33 |
| Matplotlib receivers | 24 |
| Pandas receivers | 20 |
| Python container methods | 15 |
| Conversion boundaries | 14 |
| Branch-dependent IO receivers | 13 |
| Regular-expression receivers | 13 |

## Release Disposition

| Disposition | Records | Meaning |
|---|---:|---|
| Required 1.0.5 repair queue | 430 | Evidence-backed owner is available and must be resolved before release. |
| Documented framework payload boundary | 4 | `request.json.get(...)`, retained until general protocol inference is available. |
| Ground truth correction | 0 | No current record requires a label change. |
| **Total** | **434** | |

The generated
[`failure-dispositions.md`](failure-dispositions.md) report is the
machine-derived queue by project, category, and repair scope. Inter-procedural
receiver cases are architectural limitations, but they are not GT ambiguity
when reviewed source context or a dynamic probe establishes the callable
owner.

## Recommended Repair Order

1. Resolve the 177 same-scope result and Python protocol records using
   receiver-shape and result contracts, without method-name-only promotion.
2. Reduce the 231 bounded receiver-flow records through convergent parameters,
   local returns, attributes, and homogeneous container items.
3. Preserve the 16 conservative `unknown` identities and repair the six local
   callable identity failures without unsupported guesses.
4. Keep the four Flask payload records as visible accepted boundaries.
5. Re-run the failure classifier after every batch and amend fixes belonging
   to the same repair theme into one commit.

## Release Validation

Every repair batch must preserve these checks:

```bash
python -m pytest -q
python scripts/add_verification_levels.py --check
python scripts/verify_ground_truth_calls.py --coverage-only
python scripts/refresh_ground_truth_snapshots.py --all --check
python scripts/evaluate_ground_truth.py --view all
python scripts/classify_ground_truth_failures.py --check
python scripts/diff_v1_v2.py tests/fixtures/tested_projects
```

The target is not merely a higher aggregate recall. Each reduction must map
to a reviewed mismatch family, keep call coverage complete, preserve zero
illegal keys, and avoid replacing `unknown` with unsupported guesses.
