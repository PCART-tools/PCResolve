# Ground Truth Evaluation (1.0.5)

PCResolve 1.0.5 is building a ground-truth evaluation set drawn from a
42-project fixture corpus.  The current locked pilot set contains 4
projects (626 annotated calls).  Remaining projects are pending
expansion.

**Target corpus:** 42 real Python projects (`tests/fixtures/tested_projects/`)
**Locked pilots:** `click1`, `flask2`, `hfhd`, `Youtube`
**Expansion candidates:** `AIBO`, `allnews`, and others (see `ground_truth/projects.json`)

The core question: given a call expression, does PCResolve correctly
identify its primary owner (`top_library`) as an import-backed library,
`python`, `local`, or `unknown`?

Symbol provenance, library usage aggregation, and inter-procedural
propagation are out of scope for 1.0.5 ground truth.

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

## Locked Pilots (1.0.5)

| Project | Calls | all P | all R | all F1 | library R | python R | local R |
|---------|-------|-------|-------|--------|-----------|----------|---------|
| `click1` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `flask2` | 73 | 1.000 | 0.904 | 0.950 | 1.000 | 0.720 | 1.000 |
| `hfhd` | 444 | 0.995 | 0.930 | 0.962 | 0.894 | 1.000 | 1.000 |
| `Youtube` | 104 | 0.989 | 0.837 | 0.906 | 0.775 | 0.869 | 1.000 |

Aggregate: 626 calls, 0 FP, recall 0.912. All 4 pilots locked with
`verification_level` coverage and dynamic probe evidence.
