# Phase 7B/8B Real-Project Validation

## Baseline Coverage

13 projects across 7 ecosystems, covering web, data, ML, IO/async, and
scientific workloads.  All baselines gate at exit 0 (regressions within
recorded limits, zero illegal keys).

| Project | Ecosystem | Files | Calls | R | I | P | Notes |
|---------|-----------|-------|-------|---|---|---|-------|
| click1 | web/CLI | 1 | 5 | 0 | 0 | 0 | Clean |
| flask1 | web | 2 | 7 | 0 | 0 | 0 | Clean |
| django | web/async | 1 | 43 | 0 | 0 | 0 | Fully resolved (7B-lite PR 1) |
| tensorflow1 | ML | 1 | 15 | 0 | 0 | 0 | Clean |
| Deep-Graph-Kernels | ML/scientific | 7 | 79 | 0 | 0 | 0 | Clean |
| qho | scientific | 2 | 71 | 0 | 0 | 0 | Clean |
| simulation | scientific | 8 | 207 | 0 | 0 | 0 | Fully resolved (7B-lite PR 1) |
| covid19 | data | 1 | 89 | 3 | 0 | 0 | DataFrame variable provenance |
| political-polarisation | data/vis | 1 | 69 | 12 | 2 | 0 | pandas chains; WordCloud → wordcloud (7B-lite) |
| hfhd | scientific | 6 | 444 | 4 | 20 | 1 | 7B-lite PR 1 reduced from 8 |
| MAHE_OD_DATASET | ML/vision | 13 | 480 | 16 | 3 | 10 | 7B-lite PR 1 reduced from 17 |
| greenbenchmark | data/energy | 11 | 489 | 150 | 3 | 0 | 7B-lite PR 1 reduced from 157 |
| polire | scientific | 35 | 421 | 18 | 0 | 0 | self.model/self.ok class field provenance |

**Totals**: 203 regressions, 28 improvements, 11 precision changes, 0 illegal keys.
**Legend**: R=regressions, I=improvements, P=precision changes

## Current Taxonomy (--taxonomy)

```
third-party API loss: 191
  attribute_method: 176
  container/subscript: 9
  bare_call: 6
local-to-unknown: 12
```

## Regression Categories

### 1. Local variable method calls (v2 scope isolation — expected)

v1 leaked function parameters and local variables into module-level
symbol tables.  v2 correctly isolates them, which means method chains
on local variables that v1 happened to classify via scope pollution
are now `"local"` or `"unknown"`.  7B-lite PR 1 reduced some of these
via comprehension/attribute-chain receiver propagation.

Seen in: greenbenchmark (150), political-polarisation (12), hfhd (4),
covid19 (3).

### 2. DataFrame/Tensor variable provenance not yet resolved

Chained method/subscript on variables assigned from pandas/torch that
were NOT traced through a constructor arg or wrapper method body.
Full CallGraph / return-object tracking would help.

Seen in: greenbenchmark (150), MAHE_OD_DATASET (16).

### 3. Factory-returned instances not yet supported

`c = make_client(); c.method()` where `make_client()` returns a class
instance — the factory function hides the constructor call-site
position.  Requires full CallGraph return-object tracking (Phase 7B).

### 4. Dynamic / runtime API calls

Calls through `getattr()`, `importlib.import_module()`, or other
dynamic dispatch are inherently unresolvable by static analysis alone.

## Improvements (v2 correctly resolves what v1 missed)

| Count | Typical case |
|-------|-------------|
| 20 (hfhd) | Local function return-value propagation through parameters (7A-lite) |
| 3 (MAHE) | Class constructor → instance method (7B-lite) |
| 2 (political-polarisation) | `WordCloud(...)` → wordcloud (7B-lite) |
| 3 (greenbenchmark) | Local function parameter propagation |

## Known Limitations Deferred to Future Phases

| Limitation | Phase |
|------------|-------|
| Factory-returned instances | 7B CallGraph |
| Method-level `decorated_by` on instance calls | 7B class resolution |
| `Class.method` return_sources (no bare-name collision) | 7B `FunctionId` |
| Top-level flow-sensitive reassignment | 6 CFG (optional) |
| Runtime attribute / `getattr` calls | not in scope |

## Taxonomy Semantics

The `--taxonomy` flag separates regressions into two tiers:

| Tier | Meaning | Priority |
|------|---------|----------|
| `third-party API loss` | v1 attributed a call to a library, v2 lost it (`library → local/unknown`) | High — these are real provenance gaps |
| `local-to-unknown` | v1 attributed to local, v2 changed to unknown (`local → unknown`) | Low — scope precision changes, not library loss |

The `regressions` gate number includes **both** tiers.  Reduction sprints
should target `third-party API loss / attribute_method` specifically, not
the raw gate total.

## Baseline Gate Usage

```bash
# Create/update baselines after an improvement
python scripts/diff_v1_v2.py --save-baseline tests/fixtures/tested_projects/<project>

# Run the full 13-project gate (Bash)
python scripts/diff_v1_v2.py \
  tests/fixtures/tested_projects/flask1 \
  tests/fixtures/tested_projects/click1 \
  tests/fixtures/tested_projects/django \
  tests/fixtures/tested_projects/tensorflow1 \
  tests/fixtures/tested_projects/simulation \
  tests/fixtures/tested_projects/hfhd \
  tests/fixtures/tested_projects/covid19 \
  tests/fixtures/tested_projects/qho \
  tests/fixtures/tested_projects/greenbenchmark \
  tests/fixtures/tested_projects/political-polarisation \
  tests/fixtures/tested_projects/Deep-Graph-Kernels \
  tests/fixtures/tested_projects/MAHE_OD_DATASET \
  tests/fixtures/tested_projects/polire
# exit 0 if regressions <= baseline AND illegal_keys == 0

# PowerShell equivalent (13 projects, explicit)
# $projects = @("click1","covid19","Deep-Graph-Kernels","django","simulation",
#   "flask1","greenbenchmark","hfhd","MAHE_OD_DATASET","polire",
#   "political-polarisation","qho","tensorflow1")
# $paths = $projects | ForEach-Object { "tests/fixtures/tested_projects/$_" }
# python scripts/diff_v1_v2.py @paths

# Analyse regression patterns (does not affect gate)
python scripts/diff_v1_v2.py --taxonomy tests/fixtures/tested_projects/greenbenchmark
```
