# Phase 7B/8B Real-Project Validation

## Baseline Coverage

13 projects across 7 ecosystems, covering web, data, ML, IO/async, and
scientific workloads.  All baselines gate at exit 0 (regressions within
recorded limits, zero illegal keys).

| Project | Ecosystem | Files | Calls | R | I | P | Notes |
|---------|-----------|-------|-------|---|---|---|-------|
| click1 | web/CLI | 1 | 5 | 0 | 0 | 0 | Clean |
| flask1 | web | 2 | 7 | 0 | 0 | 0 | Clean |
| django | web/async | 1 | 43 | 2 | 0 | 0 | tornado class instances |
| tensorflow1 | ML | 1 | 15 | 0 | 0 | 0 | Clean |
| Deep-Graph-Kernels | ML/scientific | 7 | 79 | 0 | 0 | 0 | Clean |
| qho | scientific | 2 | 71 | 0 | 0 | 0 | Clean |
| covid19 | data | 1 | 89 | 3 | 0 | 0 | DataFrame variable provenance |
| political-polarisation | data/vis | 1 | 69 | 12 | 2 | 0 | pandas chains; WordCloud → wordcloud (7B-lite) |
| MAHE_OD_DATASET | ML/vision | 13 | 480 | 17 | 3 | 10 | torch/torchvision var provenance |
| hfhd | scientific | 6 | 444 | 8 | 20 | 1 | Local function propagation improvements |
| simulation | scientific | 8 | 207 | 2 | 0 | 0 | Minimal noise |
| greenbenchmark | data/energy | 11 | 489 | 157 | 3 | 0 | Heavy pandas/polars DataFrame chaining |
| polire | scientific | 35 | 421 | 18 | 0 | 0 | GP/NSGP re-export edge cases |

**Legend**: R=regressions, I=improvements, P=precision changes

## Regression Categories

### 1. v2 scope is more conservative (expected)

v1 leaked function parameters and local variables into module-level
symbol tables.  v2 correctly isolates them, which means method chains
on local variables (`df.head()`, `item.replace()`) that v1 happened
to classify via scope pollution are now `"local"` or `"unknown"`.

Seen in: greenbenchmark (157), political-polarisation (12), hfhd (8),
covid19 (3).

### 2. DataFrame/Tensor variable provenance not yet resolved

Chained method calls on variables assigned from pandas/polars/torch
operations that were NOT traced through a constructor arg or wrapper
method body.  Full CallGraph / return-object tracking in 7B would
help.

Seen in: greenbenchmark, MAHE_OD_DATASET (17).

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
