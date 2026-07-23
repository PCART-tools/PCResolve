# Ground Truth Evaluation (1.0.5)

PCResolve 1.0.5 evaluates call ownership against a ground-truth set drawn
from a 42-project fixture corpus. All 42 projects are locked. The set contains
5,788 annotated calls with complete evidence and complete AST call coverage.

**Target corpus:** 42 real Python projects (`tests/fixtures/tested_projects/`)
**Locked projects:** 42/42 (see `ground_truth/projects.json`)
**Coverage:** 5,788/5,788 AST calls, 0 missing, 0 stale
**Current result:** 5,380 primary hits, 408 primary misses, recall 0.930

The core question: given a call expression, does PCResolve correctly
identify its primary owner (`top_library`) as an import-backed library,
`python`, `local`, or `unknown`?

Standalone symbol provenance and library usage aggregation are out of scope
for 1.0.5 scoring. Bounded inter-procedural evidence is used when it changes
call-site ownership.

## Data Layout

| Location | Role |
|----------|------|
| `ground_truth/calls/*.jsonl` | **Machine source of truth** — one JSON line per call record with `expected_kind`, `expected_top_library`, `status`, `verification_level`, etc. |
| `ground_truth/review/*.md` | **Version-controlled human audit views** — generated Markdown grouped by `verification_level`, plus cross-cutting `suspicious.md`. |
| `ground_truth/verification/` | Coverage check JSON, suspicious selector JSON, probe output logs. |
| `ground_truth/probes/` | Minimal dynamic probe scripts that verify receiver object ownership without running full projects. |

See [ground_truth/README.md](../ground_truth/README.md) for the full
schema, scoring contract, labeling conventions, and pilot results.

## Common Commands

```bash
# AST coverage check + suspicious GT selector
python scripts/verify_ground_truth_calls.py
python scripts/verify_ground_truth_calls.py --project hfhd --coverage-only

# Lock integrity check
python scripts/add_verification_levels.py --check

# Regenerate human review views
python scripts/render_ground_truth_review.py
python scripts/render_ground_truth_review.py --project hfhd

# Evaluate PCResolve against ground truth
python scripts/evaluate_ground_truth.py
python scripts/evaluate_ground_truth.py --project hfhd --view library
```

## Locked Evaluation Set (1.0.5)

The generated [review index](../ground_truth/review/README.md) contains the
current per-project call counts, evidence-level breakdown, and suspicious
record counts. Canonical labels remain in `ground_truth/calls/*.jsonl`.

The aggregate result is 5,380 primary hits from 5,788 calls, for recall
0.930. Of the 408 misses, 404 form the evidence-backed repair queue. Four
accepted static-analysis boundaries remain visible in the scored misses
rather than being removed from evaluation.
