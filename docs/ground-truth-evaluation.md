# Ground Truth Evaluation (1.0.5)

PCResolve 1.0.5 evaluates call ownership against a ground-truth set drawn
from a 42-project fixture corpus. All 42 projects are locked. The set contains
5,788 annotated calls with complete evidence and complete AST call coverage.

**Target corpus:** 42 real Python projects (`tests/fixtures/tested_projects/`)
**Locked projects:** 42/42 (see `ground_truth/projects.json`)
**Coverage:** 5,788/5,788 AST calls, 0 missing, 0 stale
**Current result:** 5,548 primary hits, 240 primary misses, recall 0.959

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
| `ground_truth/verification/` | Release dispositions, source-boundary reviews, failure analysis, and retained probe evidence. |
| `ground_truth/probes/` | Minimal dynamic probe scripts that verify receiver object ownership without running full projects. |

See [ground_truth/README.md](../ground_truth/README.md) for the full
schema, scoring contract, labeling conventions, and locked evaluation results.

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

The aggregate result is 5,548 primary hits from 5,788 calls, for recall
0.959. All 240 primary misses have independent source review and an
`accepted_unknown` disposition. They remain visible in the scored misses
rather than being removed from evaluation.

Verification levels alone do not justify a release disposition. A dynamic
probe confirms runtime ownership, not static irrecoverability. Every accepted
boundary therefore also requires project-source evidence showing why the exact
owner cannot be established under the pure-static contract.

Independent boundary decisions are stored in
`ground_truth/verification/static-boundary-reviews.json`. Each decision names
the exact call records and carries a digest over every Python source in the
project. Source, call identity, expected owner, or analyzer-outcome drift makes
the release gate fail until the boundary is reviewed again.

Exact owners supported by project source must become primary hits.
Evidence-limited records must be independently reviewed before receiving an
`accepted_unknown` disposition. The current snapshot satisfies the final gate
with `fix_1_0_5=0` and `ground_truth_correction=0`:

```bash
python scripts/classify_ground_truth_failures.py --release-check
```
