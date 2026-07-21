# PCResolve 1.0.5 Ground Truth Failure Analysis

Snapshot: 2026-07-21, after the first ownership repair batch

## Executive Summary

The locked evaluation set contains 5,788 call records across 42 projects.
PCResolve currently produces 5,254 primary hits and 534 primary mismatches,
for recall 0.908. AST coverage is complete at 5,788/5,788, with no missing,
stale, or uncovered call predictions. The remaining failures are ownership
classification failures, not call collection failures.

The first repair batch corrected ten outer `super().__init__()` labels and
six directly imported `ViewClient(...)` constructor labels. It also protects
external dotted import evidence from local wildcard fallback and preserves
structured `python`, `local`, and `unknown` terminal results. Four remaining
records are the documented `request.json.get(...)` framework payload
boundary. The non-boundary repair queue therefore contains 530 records.

## First Repair Batch

| Change | Records | Result |
|---|---:|---|
| External dotted import ownership under local wildcard fallback | 136 | Android `ViewClient` constructors and receiver methods now retain `com` ownership |
| Structured terminal ownership under external wildcard imports | 3 primary hits | Python/local terminal results are no longer reinterpreted as the wildcard library |
| Corrected outer `super().__init__()` GT labels | 10 | Outer local base-method calls are `local`; nested `super()` remains `python` |
| Corrected imported `ViewClient(...)` GT labels | 6 | Directly imported constructor calls are `library/com` |

## Classification By Analyzer Outcome

| Current reason | Records | Share | Failure mechanism |
|---|---:|---:|---|
| `LOCAL_DEFINITION` | 393 | 73.6% | A parameter, local binding, or attribute is treated as proof that the callable implementation is project-local. |
| `UNRESOLVED` | 74 | 13.9% | Receiver ownership is lost through parameters, return values, branches, attributes, subscripts, or chains. |
| `TRANSITIVE_IMPORT` | 50 | 9.4% | Import provenance of a producer or enclosing object leaks into the callable owner. |
| `RETURN_PROPAGATION` | 17 | 3.2% | The called function's owner is propagated to a result object whose callable surface has a different owner. |
| **Total** | **534** | **100.0%** | |

### `LOCAL_DEFINITION` Overreach

This is the dominant failure. A receiver name bound in project code is often
resolved to `local`, and the classification pipeline gives that result the
highest priority. This conflates two different facts:

1. The receiver binding is local to the project.
2. The method implementation is owned by the receiver's runtime class.

Examples include `vc.dump()` on an Android ViewClient object,
`train.set_index()` on a pandas object, `tensor.dim()` on a torch Tensor,
`m.group()` on a regular-expression match, and `title.strip()` on a Python
string. In each case the variable is local, but the callable owner is not.

### `UNRESOLVED` Receiver Loss

These records preserve uncertainty instead of guessing, but they still miss
evidence-backed GT owners. Common loss points are function parameters, local
function returns, nested attributes, subscript results, and chained calls.
Examples include matplotlib calls in AIBO, Flask client calls, pandas group
operations, torch tensor chains, SciPy sparse methods, and NumPy array methods.

### `TRANSITIVE_IMPORT` Producer Leakage

The analyzer follows an import-backed source but does not separate producer
ownership from result-object ownership. Typical errors include:

* A string produced by `re` remains owned by `re` for `.replace()`.
* An argparse attribute remains owned by `argparse` for `.split()` or
  `.lower()`.
* `request.json.get()` remains owned by Flask instead of the mapping protocol.
* Project-local methods on objects carrying Box2D state become Box2D-owned.

### `RETURN_PROPAGATION` Result Leakage

The same producer/result distinction appears explicitly on call results.
Examples include JSON-decoded dictionaries used with `.get()`, XML text used
with string methods, regex-produced strings, argparse string attributes, and
local wrapper results inheriting the wrapped library owner.

## Classification By Semantic Family

| Semantic family | Records | Share | Included GT categories |
|---|---:|---:|---|
| Library receiver ownership not propagated | 308 | 57.7% | pandas, NumPy, torch, matplotlib, regex, SciPy, GPy, Box2D, Android ViewClient parameters, multiprocessing, database, and conversion receivers |
| Python builtin or protocol ownership not propagated | 194 | 36.3% | String, list, dict, set, generic protocol, builtin callable, and library-produced builtin values |
| Branch-dependent or polymorphic owner should remain unknown | 26 | 4.9% | File-like parameters, branch-dependent IO receivers, and unconstrained polymorphic receivers |
| Project-local callable identity overwritten by library evidence | 6 | 1.1% | Local baseline wrappers, dynamic local callables, and monkey-patched local methods |
| **Total** | **534** | **100.0%** | |

## Highest Impact Concentrations

| Concentration | Records | Primary cause |
|---|---:|---|
| `allnews` Python protocol methods | 108 | Local receiver fallback and producer leakage |
| General transitive receiver methods | 102 | Missing parameter, return, attribute, and chain propagation |
| NumPy array receivers | 49 | Array ownership lost through parameters, slicing, and local assignments |
| Python string methods | 40 | String result type not preserved |
| Torch tensor receivers | 33 | Tensor ownership lost through parameters and transforms |
| Matplotlib receivers | 30 | Import alias or returned axes ownership becomes unknown or local |
| Python container methods | 21 | Container element and result-kind ownership is not propagated |
| Remaining Android ViewClient parameters | 10 | Imported receiver ownership is lost across helper-function parameters |

## Ground Truth Corrections Completed

Ten polire outer `super().__init__(...)` records now use `local/local` because
the source classes inherit the project-local `Base` class. The separate nested
`super()` records remain `python/python`.

Six greenbenchmark `ViewClient(device, serialno, **kwargs2)` records now use
`library/com`. The callable is a directly imported external constructor, even
though its result is assigned to a project-local variable.

The allnews `functions.get(function)` record is not a GT error. `functions`
is a nested dictionary returned by `modules.get(module)`, so `.get()` is a
Python dict method. It is a valid regression case for container item and
result-kind propagation.

## Boundary Versus Repair Queue

| Disposition | Records | Meaning |
|---|---:|---|
| Documented framework payload boundary | 4 | `request.json.get(...)`, retained until protocol inference is generalized |
| Non-boundary analyzer repair queue | 530 | Evidence-backed owner is available from source context or dynamic probes |
| **Total** | **534** | |

Inter-procedural receiver cases are architectural limitations, but they are
not GT ambiguity. They remain in the non-boundary queue because the callable
owner is established by reviewed source context or a dynamic probe.

## Recommended Repair Order

1. Separate local binding provenance from local callable identity. Only an
   explicitly resolved project function, class, or method should trigger the
   `LOCAL_DEFINITION` early exit.
2. Propagate receiver ownership through parameters, assignments, attributes,
   subscripts, and local returns before adding broader call-graph inference.
3. Model Python protocol result kinds for standard-library guarantees such as
   dict values, string operations, decoded JSON, regex text, and argparse
   values without relying on method-name-only heuristics.
4. Separate producer owner from result-object owner for
   `TRANSITIVE_IMPORT` and `RETURN_PROPAGATION` paths.
5. Preserve `unknown` for genuinely branch-dependent or unconstrained
   receivers instead of defaulting them to local or an imported producer.
6. Protect project-local callable identity from receiver member-state or
   argument provenance.
7. Revisit the four Flask payload boundary records only after the general
   protocol rules are stable.

## Release Validation

Every repair batch must preserve these checks:

```bash
python -m pytest -q
python scripts/add_verification_levels.py --check
python scripts/verify_ground_truth_calls.py --coverage-only
python scripts/evaluate_ground_truth.py --view all
python scripts/diff_v1_v2.py tests/fixtures/tested_projects
```

The target is not merely a higher aggregate recall. Each reduction must map
to a reviewed mismatch family, keep call coverage complete, preserve zero
illegal keys, and avoid replacing `unknown` with unsupported guesses.
