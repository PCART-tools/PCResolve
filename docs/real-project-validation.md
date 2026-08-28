# PCResolve Real-Project Validation

PCResolve uses locked call-site ground truth from 42 real-world projects.
The evaluation contains 5,788 call expressions with complete AST coverage.
It measures primary callable or receiver ownership; standalone symbol
provenance is evaluated only when it affects call classification.

## Evaluation

```bash
python scripts/evaluate_ground_truth.py --view all
python scripts/verify_ground_truth_calls.py --coverage-only
python scripts/add_verification_levels.py --check
python scripts/refresh_ground_truth_snapshots.py --all --check
```

The gate requires 100% AST call coverage, locked annotations, valid
verification evidence, and zero stale project snapshots.

## Current Summary

```text
Projects:          42
GT records:        5,788
Primary hits:      5,546
Primary misses:      242
Primary recall:    0.958
False positives:       0
AST coverage:      100%
```

The canonical labels live in `ground_truth/calls/`. Human-readable review
views live in `ground_truth/review/`, and release dispositions for unresolved
records live in `ground_truth/verification/`.

## Evidence Boundary

Ground truth records semantic or runtime ownership. Release disposition asks
whether that owner is recoverable from project source under PCResolve's
pure-static contract. Runtime-only owners may remain scored misses when the
honest static result is `unknown`; the analyzer does not add library-specific
return-type guesses to force a hit.

See [Ground Truth Evaluation](./ground-truth-evaluation.md) for the annotation
schema and review workflow.
