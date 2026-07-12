# Ground Truth Evaluation (1.0.5)

PCResolve 1.0.5 is building a ground-truth evaluation set drawn from a
42-project fixture corpus. The current locked evaluation set contains 11
projects and 815 annotated calls. Remaining projects are pending expansion.

**Target corpus:** 42 real Python projects (`tests/fixtures/tested_projects/`)
**Locked projects:** `click1`, `click2`, `django`, `flask1`, `flask2`,
`hfhd`, `machine-learning`, `psycopg2`, `redis`, `tensorflow1`, `Youtube`
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
| `click2` | 8 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `django` | 44 | 1.000 | 0.705 | 0.827 | 0.783 | 0.636 | 0.600 |
| `flask1` | 7 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | n/a |
| `flask2` | 73 | 1.000 | 0.945 | 0.972 | 1.000 | 0.826 | 1.000 |
| `hfhd` | 444 | 0.998 | 0.930 | 0.963 | 0.894 | 1.000 | 1.000 |
| `machine-learning` | 43 | 0.954 | 0.954 | 0.954 | 0.935 | 1.000 | 1.000 |
| `psycopg2` | 39 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `redis` | 33 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `tensorflow1` | 15 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| `Youtube` | 104 | 1.000 | 0.923 | 0.960 | 0.800 | 1.000 | 1.000 |

Aggregate: 815 calls, 757 primary hits, 58 primary misses, recall 0.929.
All 11 projects are locked with complete verification evidence and 815/815
AST call coverage.
