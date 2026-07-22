# PCResolve 1.0.5 Ground Truth Failure Analysis

Snapshot: 2026-07-22, after the second ownership repair batch

## Executive Summary

The locked evaluation set contains 5,788 call records across 42 projects.
PCResolve currently produces 5,320 primary hits and 468 primary mismatches,
for recall 0.919. AST coverage is complete at 5,788/5,788, with no missing,
stale, or uncovered call predictions. The remaining failures are ownership
classification failures, not call collection failures.

The second repair batch separates callable ownership from result-object
ownership across standard-library results, local container returns, selected
library conversions, Matplotlib objects, and builtin subclasses. It repairs
68 previously missed records. Two Polire NumPy calls that were correct only by
an unsupported producer-owner guess now remain `unknown`, for a net reduction
of 66 mismatches. One JSON GT record was corrected without changing whether
the call was a hit.

Four remaining records are the documented `request.json.get(...)` framework
payload boundary. The non-boundary repair queue therefore contains 464
records.

## Second Repair Batch

| Change | Prior misses repaired | Result |
|---|---:|---|
| Python-owned standard-library results | 41 | Regex strings and decoded JSON values no longer retain the producer module as receiver owner |
| Local Python container returns and builtin subclasses | 6 | Dict/list results and inherited builtin container methods classify as `python` without method-name-only guessing |
| Flask result-object propagation | 15 | Evidence-backed Flask receivers retain `flask` ownership across local returns |
| Function-local Matplotlib result chains | 6 | Axes methods retain `matplotlib` after `gcf().add_subplot(...)` assignments |
| Conservative NumPy ufunc boundary | -2 | Unresolved receiver-preserving ufunc results remain `unknown` instead of inheriting `numpy` from the callable |
| **Net mismatch reduction** | **66** | Recall improves from 0.908 to 0.919 |

The result-owner contracts distinguish the called function from the object it
returns. They also distinguish a Python tuple result from its unpacked items.
For example, `scipy.linalg.svd()` is SciPy-owned, its aggregate return is a
Python tuple, and its three statically uniform unpacked items are NumPy-owned.

## Classification By Analyzer Outcome

| Current reason | Records | Share | Failure mechanism |
|---|---:|---:|---|
| `LOCAL_DEFINITION` | 365 | 78.0% | A parameter, local binding, or attribute is treated as proof that the callable implementation is project-local. |
| `UNRESOLVED` | 59 | 12.6% | Receiver ownership is lost through parameters, return values, branches, attributes, subscripts, or chains. |
| `TRANSITIVE_IMPORT` | 37 | 7.9% | Import provenance of a producer or enclosing object leaks into the callable owner. |
| `RETURN_PROPAGATION` | 7 | 1.5% | A called function's owner is propagated to a result object whose callable surface has a different owner. |
| **Total** | **468** | **100.0%** | |

### `LOCAL_DEFINITION` Overreach

This remains the dominant failure. A receiver name bound in project code is
often resolved to `local`, even when its runtime class is owned by an imported
library or Python itself. Examples include pandas DataFrames, NumPy arrays,
torch Tensors, regular-expression matches, and Python strings or containers.

### `UNRESOLVED` Receiver Loss

These records preserve uncertainty instead of guessing. Common loss points
are function parameters, local function returns, nested attributes, subscript
results, and chained calls. The two Polire `s_vec.sum()` records are now in
this group because `s_vec` comes from a local method whose NumPy result depends
on unresolved parameters.

### Producer And Result Leakage

`TRANSITIVE_IMPORT` and `RETURN_PROPAGATION` failures still conflate a
producer with its returned object. Remaining examples include argparse values,
XML text, local wrappers, and protocol-bearing library results that do not yet
have a general static contract.

## Classification By Expected Kind

| Expected kind | Records | Share | Typical missing evidence |
|---|---:|---:|---|
| `library` | 289 | 61.8% | Receiver type through parameters, returns, attributes, conversions, and chains |
| `python` | 147 | 31.4% | Builtin string, container, mapping, and protocol object identity |
| `unknown` | 26 | 5.6% | Branch-dependent or unconstrained polymorphic receivers |
| `local` | 6 | 1.3% | Project-local callable identity overwritten by library evidence |
| **Total** | **468** | **100.0%** | |

## Highest Impact Concentrations

| Concentration | Records | Primary cause |
|---|---:|---|
| General transitive receiver methods | 87 | Missing parameter, return, attribute, and chain propagation |
| Python protocol methods | 71 | Receiver protocol identity is not propagated |
| NumPy array receivers | 51 | Array ownership is lost through parameters, slicing, and local assignments |
| Python string methods | 36 | String result identity is not preserved through every local path |
| Torch tensor receivers | 33 | Tensor ownership is lost through parameters and transforms |
| Matplotlib receivers | 24 | Function-local imports or returned plotting objects remain unresolved |
| Pandas receivers | 21 | DataFrame and Series ownership is lost across local functions |
| Branch-dependent IO receivers | 17 | File-like owner depends on runtime branch selection |
| Python container methods | 15 | Container item and result-kind ownership is not propagated |

## Ground Truth Correction

`json.load(data_file).get(serialno)` is now `python/python`. The `json.load`
call remains `library/json`, while the successful `.get()` dispatch is owned
by the Python mapping returned by the default JSON decoder. The record is
`static_context`, not `static_obvious`, because the receiver identity depends
on the standard-library return contract.

## Boundary Versus Repair Queue

| Disposition | Records | Meaning |
|---|---:|---|
| Documented framework payload boundary | 4 | `request.json.get(...)`, retained until protocol inference is generalized |
| Non-boundary analyzer repair queue | 464 | Evidence-backed owner is available from reviewed source context or dynamic probes |
| **Total** | **468** | |

Inter-procedural receiver cases are architectural limitations, but they are
not GT ambiguity. They remain in the repair queue because the callable owner
is established by reviewed source context or a dynamic probe.

## Recommended Repair Order

1. Propagate receiver ownership through local parameters and return values
   using call-site evidence, without turning PCResolve into a full call graph.
2. Carry import-backed and Python protocol identity through attributes,
   subscripts, and homogeneous container items.
3. Preserve result-object contracts for standard-library and probe-backed
   conversions without broad method-name heuristics.
4. Keep unresolved polymorphic or branch-dependent receivers as `unknown`.
5. Protect project-local callable identity from receiver member-state or
   argument provenance.
6. Revisit the four Flask payload boundary records only after general mapping
   protocol inference is stable.

## Release Validation

Every repair batch must preserve these checks:

```bash
python -m pytest -q
python scripts/add_verification_levels.py --check
python scripts/verify_ground_truth_calls.py --coverage-only
python scripts/evaluate_ground_truth.py --all --view all
python scripts/diff_v1_v2.py tests/fixtures/tested_projects
```

The target is not merely a higher aggregate recall. Each reduction must map
to a reviewed mismatch family, keep call coverage complete, preserve zero
illegal keys, and avoid replacing `unknown` with unsupported guesses.
