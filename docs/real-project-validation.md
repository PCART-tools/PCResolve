# PCResolve 1.0.4 Real-Project Validation

42 real-world projects audited. 21 hard baselines with recorded
regression/improvement/precision counts. Zero crashes, zero
timeouts, zero illegal keys.

## Gate

```bash
python scripts/diff_v1_v2.py tests/fixtures/tested_projects
```

- Projects with a baseline JSON in `tests/fixtures/diff_baselines/`
  must have `R <= baseline` and `illegal=0`.  Exceeding the baseline
  fails the gate.
- Projects without a baseline display `[PENDING]` and are
  informational only (not a hard failure).

## Audit

```bash
python scripts/audit_tested_projects.py
```

Full report: `reports/tested-projects-audit.json` /
`reports/tested-projects-audit.md`.

## 1.0.4 Summary

```text
Projects audited:    42
Crashed/timeout:     0
Illegal key projects: 0
Hard baselines:      21 (all [OK])
Total API calls:     ~5,700
Unique libraries:    104
Regressions:         303
Improvements:        147
Precision changes:    29
Illegal keys:         0
```

## Hard Baselines (21 projects)

| Project | Calls | Libs | R | I | P | Ecosystem |
|---------|-------|------|---|---|---|-----------|
| AIBO | 647 | 22 | 20 | 26 | 0 | scientific |
| allnews | 986 | 30 | 80 | 22 | 14 | NLP |
| barcoded_yeast_reanalysis | 328 | 11 | 2 | 6 | 0 | scientific |
| click1 | 5 | 1 | 0 | 0 | 0 | CLI |
| covid19 | 89 | 9 | 0 | 1 | 3 | data |
| Deep-Graph-Kernels | 79 | 5 | 0 | 0 | 0 | ML |
| django | 43 | 7 | 0 | 4 | 0 | web |
| ex_4_2 | 207 | 8 | 0 | 0 | 0 | scientific |
| final | 314 | 9 | 1 | 10 | 0 | web |
| flask1 | 7 | 1 | 0 | 0 | 0 | web |
| greenbenchmark | 489 | 13 | 150 | 3 | 0 | data |
| hfhd | 444 | 7 | 4 | 20 | 1 | scientific |
| MAHE_OD_DATASET | 480 | 17 | 19 | 5 | 10 | ML/vision |
| polire | 421 | 16 | 5 | 17 | 1 | scientific |
| political-polarisation | 69 | 6 | 12 | 2 | 0 | data |
| Python-Workshop | 172 | 4 | 0 | 3 | 0 | edu |
| qho | 71 | 4 | 0 | 0 | 0 | scientific |
| scrapping | 110 | 3 | 0 | 16 | 0 | web |
| SDOML | 94 | 10 | 2 | 0 | 0 | ML |
| tensorflow1 | 15 | 1 | 0 | 0 | 0 | ML |
| Youtube | 104 | 12 | 2 | 2 | 0 | web |

## Taxonomy (--taxonomy)

```text
third_party_api_loss: 303
  third-party -> local:   189
  third-party -> unknown: 114
local_precision_change:
  local -> third-party:  147
  local -> unknown:       12
precision:                29
```

## Regression Categories

### Scope isolation (expected)
v1 leaked function-local bindings into module-level symbol tables.
v2 correctly isolates them. Method chains on local variables that
v1 classified via scope pollution are now `local` or `unknown`.

### Container/chained-method provenance
Subscript and chained method calls on local variables holding
third-party values cannot always be traced through the full
propagation path.  SourceSet alternatives preserve the candidates.

### Multi-third-party returns
Functions returning different third-party objects from different
branches produce conservative primaries with complete alternatives
in `library_usage`.

## Improvements

v2 correctly resolves provenance that v1 missed: local function
return-value propagation, constructor-arg → self.attr → method
call, and decorator evidence tracking.
