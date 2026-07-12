# PCResolve 1.0.5 Ground Truth Evaluation

Real-project ground truth for evaluating PCResolve's library API
call ownership accuracy (recall, precision, ownership accuracy).

## Scope

We evaluate **call-site classification**: given a call expression in a
Python file, does PCResolve correctly identify:

1. The call's `expected_kind` (library / python / local / unknown)
2. Which top-level library it belongs to (`top_library`)
3. Auxiliary evidence (`alternatives`, `decorated_by`)

Symbol provenance, library usage aggregation, and inter-procedural
propagation are out of scope for 1.0.5 ground truth.

GT only judges the callable's ownership identity.  `expected_kind`
captures whether the owner is an import-backed library, a Python
builtin, a project-local callable, or unknown.  `expected_top_library`
captures the precise owner name.  No distinction between stdlib and
PyPI is required: `json.loads()`, `pathlib.Path()`, `requests.get()`,
and `numpy.array()` are all `expected_kind="library"`.

## Candidate Sources

PCResolve generates an initial candidate file containing every call
it detected.  These are marked `source: "pcresolve_candidate"`.
Human annotators may add calls that PCResolve missed as
`source: "manual_gt"`.  The evaluator uses both to compute recall
(manual GT calls are true positives that should have been found).

## Call Status Labels (truth)

| `status` | Meaning |
|----------|---------|
| `positive` | Should be included in GT evaluation as a call-ownership case. |
| `negative` | Should NOT be counted in the current GT evaluation view. |
| `ambiguous` | Library ownership cannot be uniquely determined statically. |
| `unsupported` | Beyond 1.0.5 static analysis scope (dynamic import, monkey-patch, runtime reflection, framework injection). Excluded from core metrics. |

## Annotation Workflow Status

| `annotation_status` | Meaning |
|----------------------|---------|
| `draft` | Initial labeling; `expected_*` and `status` may be empty. |
| `reviewed` | Reviewed by a second annotator. All required fields populated. |
| `locked` | Finalized. No further changes without schema version bump. |

### Lock Criteria

**Lock readiness** (transition from reviewed to locked):

1. Every `positive` GT record has `verification_level` and `verification_notes`.
2. Zero records have `status="unsupported"`.
3. Zero records have `verification_level="unsupported"`.
4. `annotation_status` is uniformly `reviewed`.
5. `projects.json` status matches JSONL `annotation_status`.

**Locked integrity** (post-lock, for CI / release gate):

1. All positive records continue to satisfy the readiness criteria above.
2. `annotation_status` is uniformly `locked`.
3. `projects.json` status matches.
4. AST call coverage: 0 missing, 0 stale.

Run `python scripts/add_verification_levels.py --check` to validate either
state.  It accepts both `reviewed` and `locked` and exits non-zero on any
blocker.

### `verification_level` Semantics

| Level | Meaning | Verification method |
|-------|---------|---------------------|
| `static_obvious` | Direct import, builtin, or clearly local callable. | Automated rule confirmation (e.g. `np.array()`, `len()`, `pickle.dump()`). |
| `static_context` | Local container/protocol method, decorated local, framework public receiver surface. | Local AST and README conventions spot-check (e.g. `list.append()`, `request.json.get()`, `hello.main()`). |
| `dynamic_probe` | Chained calls involving library function return or receiver type. | Minimal runnable code using `type(receiver).__module__` or bound method module (e.g. `np.log(pd.Series).diff()`, `cdist(...).argmin()`). |
| `manual_reasoned` | Depends on project context, docstring, or library contract; hard to run. | Manual reasoning with notes and category evidence. |
| `unsupported` | Dynamic import, monkey patch, runtime injection, reflection. | Excluded from core P/R/F1; retained as coverage risk. |

## JSONL Call Record Schema

Each line in `calls/<project>.jsonl`:

```json
{
  "source": "pcresolve_candidate",
  "project": "click1",
  "file": "click_decorator.py",
  "lineno": 11,
  "col_offset": 4,
  "expression": "hello.main(standalone_mode=False)",
  "expected_kind": "local",
  "expected_top_library": "local",
  "expected_alternatives": [],
  "expected_decorated_by": ["click"],
  "status": "positive",
  "annotation_status": "locked",
  "category": "decorated_callable_receiver",
  "notes": "",
  "verification_level": "static_context",
  "verification_notes": "decorated local callable; primary identity is local, decorator evidence in decorated_by"
}
```

Manual GT entry (annotator-added call PCResolve missed):

```json
{
  "source": "manual_gt",
  "project": "click1",
  "file": "click_decorator.py",
  "lineno": 12,
  "col_offset": 4,
  "expression": "json.loads(text)",
  "pcresolve_kind": "",
  "pcresolve_top_library": "",
  "pcresolve_alternatives": [],
  "pcresolve_decorated_by": [],
  "pcresolve_reason": "",
  "pcresolve_confidence": null,
  "pcresolve_func_name": "",
  "expected_kind": "library",
  "expected_top_library": "json",
  "expected_alternatives": [],
  "expected_decorated_by": [],
  "status": "positive",
  "annotation_status": "locked",
  "category": "",
  "notes": "missed by PCResolve",
  "verification_level": "static_obvious",
  "verification_notes": "manual GT entry for direct import-backed API call"
}
```

### Field Semantics

| Field | Required | Description |
|-------|----------|-------------|
| `source` | yes | `pcresolve_candidate` or `manual_gt` |
| `project` | yes | Project identifier (matches `projects.json` key) |
| `file` | yes | File path relative to project root |
| `lineno` | yes | 1-based line number |
| `col_offset` | yes | 0-based column offset |
| `expression` | yes | Call expression string |
| `expected_kind` | reviewed+ | `library`, `python`, `local`, or `unknown` |
| `expected_top_library` | reviewed+ | Owner library name, or `local`/`python`/`unknown` |
| `expected_alternatives` | no | Acceptable alternative libraries |
| `expected_decorated_by` | no | Decorator libraries for the call |
| `status` | reviewed+ | `positive`, `negative`, `ambiguous`, or `unsupported` |
| `annotation_status` | yes | `draft`, `reviewed`, or `locked` |
| `category` | no | Semantic category for error analysis |
| `notes` | no | Free-text annotator notes |
| `verification_level` | locked | `static_obvious`, `static_context`, `dynamic_probe`, `manual_reasoned`, or `unsupported` |
| `verification_notes` | locked | Evidence summary for the assigned verification level |

`pcresolve_*` fields are pre-filled by the candidate generator as
seed data; they are never truth.  For `source="manual_gt"` entries
they are present but empty.  Evaluators must read all `pcresolve_*`
fields with `.get()` or equivalent tolerant access.

### `expected_kind` Values

| Value | Meaning | Example owners |
|-------|---------|---------------|
| `library` | Import-backed library owner | `requests`, `numpy`, `flask`, `json`, `pathlib`, `csv`, `re` |
| `python` | Builtin / Python-provided API / builtin object method / protocol-style method on container-like receiver | `len()`, `open()`, `str.strip()`, `list.append()`, `request.json.get()` when `request.json` is treated as a mapping payload |
| `local` | Project-defined callable or object | `make_session()`, `self.helper()` |
| `unknown` | Cannot be determined statically | dynamic lookup, unresolved receiver |

`python` also covers builtin/container/protocol-style methods when the receiver
is used in project code as a Python container-like value, even if the value was
obtained through an import-backed object. For example, `request.json.get(...)`
may be labeled `python` when surrounding code treats `request.json` as a mapping
payload via `in`, subscript, and `.get()`.

## Evaluation Views

The evaluator filters by `expected_kind`:

- **All ownership**: `expected_kind in ("library", "python", "local")`
- **Library only**: `expected_kind == "library"`
- **Python builtin only**: `expected_kind == "python"`
- **Local evidence**: `expected_kind == "local"` (decorated_by scoring)

No distinction between stdlib and PyPI libraries.

## Scoring Contract

All scoring uses `pcresolve_*` for PCResolve output and
`expected_*` for ground truth.  Fields are read from the joined
record (matched by project/file/lineno/col_offset/expression).

### Primary Hit

`status == "positive"`
AND `pcresolve_kind == expected_kind`
AND `pcresolve_top_library == expected_top_library`

### Candidate Hit

`status == "positive"`
AND `expected_kind == "library"`
AND `expected_top_library in pcresolve_alternatives`

Counted separately as candidate recall.

### Decorated Local Hit

`status == "positive"`
AND `expected_kind == "local"`
AND `pcresolve_top_library == "local"`
AND every library in `expected_decorated_by` appears in
`pcresolve_decorated_by`

### Primary Miss

`status == "positive"`
AND (`pcresolve_kind != expected_kind`
     OR `expected_top_library` not in
     (`pcresolve_top_library`, `pcresolve_alternatives`))

### Decorated Evidence Miss

`status == "positive"`
AND at least one library in `expected_decorated_by` is missing
from `pcresolve_decorated_by`

### Primary Identity Miss

`status == "positive"`
AND `pcresolve_kind == expected_kind`
AND `pcresolve_top_library != expected_top_library`
AND `expected_top_library` not in `pcresolve_alternatives`

### False Positive

`status == "negative"`
AND `pcresolve_kind` matches a kind in the selected evaluation view
(e.g. `pcresolve_kind == "library"` in the library-only view).

### Wrong Owner

`status == "positive"`
AND `pcresolve_kind == expected_kind`
AND `pcresolve_top_library` is a library that is not
`expected_top_library` and not in `expected_alternatives`

### local / python / unknown

- `positive` with `expected_kind="library"`: `pcresolve_kind` of
  `local`, `python`, or `unknown` is a primary miss.
- `positive` with `expected_kind="local"`: `pcresolve_kind` must be
  `local` and `pcresolve_top_library` must be `local` for a primary
  identity hit. Decorated evidence scored separately.
- `negative`: `pcresolve_kind` and `pcresolve_top_library` matching
  `local`, `python`, or `unknown` is correct.
- `unknown` on `ambiguous` is acceptable.

### unsupported

Excluded from precision and recall; counted in coverage metrics.

## Pilot Projects

All 4 pilots are **locked** (2026-06-04).  626 calls, 0 missing, 0 stale,
0 FP, aggregate recall 0.912.

### Locked Pilot Results

| Project | Calls | all P | all R | all F1 | library R | python R | local R | deco |
|---------|-------|-------|-------|--------|-----------|----------|---------|------|
| `click1` | 5 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1 |
| `flask2` | 73 | 1.000 | 0.904 | 0.950 | 1.000 | 0.720 | 1.000 | 0 |
| `hfhd` | 444 | 0.995 | 0.930 | 0.962 | 0.894 | 1.000 | 1.000 | 0 |
| `Youtube` | 104 | 0.989 | 0.837 | 0.906 | 0.775 | 0.869 | 1.000 | 0 |

### Verification Level Breakdown

| Project | static_obvious | static_context | dynamic_probe | manual_reasoned |
|---------|---------------|----------------|---------------|-----------------|
| `click1` | 4 | 1 | 0 | 0 |
| `flask2` | 48 | 25 | 0 | 0 |
| `hfhd` | 377 | 39 | 28 | 0 |
| `Youtube` | 82 | 13 | 9 | 0 |
| **TOTAL** | **511** | **78** | **37** | **0** |

### Primary Miss Categories

**flask2** (7 misses, all in python view):
- 4 × `request.json.get(...)` — mapping protocol method on Flask-derived
  payload, classified as `library/flask` by PCResolve
- 1 × `getattr(error, ...)` — Python builtin classified as `local`
- 1 × `tasks.append(task)` — list.append on local container classified as `local`
- 1 × `error_messages.get(...)` — dict.get on local container classified as `local`

**hfhd** (31 misses, 29 library + 2 wrong_owner):
- 23 × pandas Series/DataFrame methods (`.dropna()`, `.to_numpy()`,
  `.cumsum()`, `.diff()`, `.between_time()`) classified as `local`
- 6 × numpy ndarray methods (`.flatten()`, `.reshape()`) classified as `local`
- 2 × `.diff()`/`.mean()` on pandas Series result of `np.log()`,
  classified as `numpy` instead of `pandas` (wrong_owner)

**Youtube** (17 misses, 9 library + 8 python):
- 5 × `x.todense()` — scipy sparse matrix method classified as `python` or `local`
- 3 × `.copy()`/`.argmin()`/`.mean()` on numpy arrays classified as `local` or `unknown`
- 1 × `.argmin()` on numpy array classified as `scipy` (wrong_owner)
- 7 × `list.append()`/`list.extend()`/`list.index()` on local lists classified as `local`
- 1 × `list.append()` on defaultdict list classified as `collections`

**click1**: no misses — all 5 calls correctly classified.

### Miss Root Causes

| Root Cause | Projects | Example | GT | PCResolve |
|-----------|----------|---------|----|-----------|
| Mapping protocol receiver | flask2 | `request.json.get(...)` | python | library/flask |
| Builtin method on local container | flask2, Youtube | `list.append()`, `list.extend()`, `list.index()`, `dict.get()` | python | local |
| Pandas method on Series/DataFrame | hfhd | `x.dropna()`, `data.to_numpy()` | library/pandas | local |
| Numpy method on ndarray | hfhd | `arr.flatten()`, `arr.reshape()` | library/numpy | local |
| Chained owner: numpy→pandas | hfhd | `np.log(s).diff()` | library/pandas | library/numpy |
| Chained owner: cdist→numpy | Youtube | `D.argmin(axis=1)` | library/numpy | library/scipy |
| Scipy sparse method | Youtube | `x.todense()` | library/scipy | python/local |
| Builtin method on defaultdict list | Youtube | `distPartDict[k].append(v)` | python | library/collections |

### Labeling Conventions (1.0.5 Pilot)

These conventions emerged from click1/flask2/hfhd/Youtube annotation and are
fixed for 1.0.5:

**Decorated callable receiver.** `hello.main()` where `hello` is
decorated by `@click.command()`: `expected_kind="local"`,
`expected_top_library="local"`, `expected_decorated_by=["click"]`.
The decorator never changes the primary identity of the decorated target.

**Protocol/container-style receiver.** `request.json.get(...)` when
surrounding code treats `request.json` as a mapping payload (via `in`,
subscript, `.get()`): `expected_kind="python"`,
`expected_top_library="python"`.  The callable is a Python protocol
method, not a Flask-specific API.

**Framework public receiver surface.** `request.headers.get(...)`,
`app.logger.info(...)` accessed through Flask public receiver surface:
`expected_kind="library"`, `expected_top_library="flask"`.  1.0.5 GT
does not expand framework internals to werkzeug/logging.

**Conversion boundary.** `df.to_numpy()`: the call itself is
`expected_kind="library"`/`expected_top_library="pandas"`.  The GT
judges the call expression's callable owner — `.to_numpy()` is a
pandas method — not the return type.

**Builtin/container method on local receiver.** `tasks.append(...)`,
`error_messages.get(...)`: `expected_kind="python"`,
`expected_top_library="python"`.  `local` is an acceptable alternative
per the builtin/container receiver contract, but GT uses `python` as
the canonical label.

### Expansion Candidates

| Project | Rationale | Labeling Focus |
|---------|-----------|----------------|
| `AIBO` | Large project stress test | Scale, FP/FN classification |
| `allnews` | Large NLP/ML project | NER, WikiExtractor, performance at scale |

## Verification Tooling (1.0.5)

### AST Call Coverage Checker

`scripts/verify_ground_truth_calls.py` extracts every `ast.Call` from pilot
source files independently and compares against GT JSONL records.

Matching is **multiset**: records are grouped by `(file, lineno, col_offset)`,
then matched within each position by **normalized expression**.  When
expression matching is exhausted and per-position counts are equal, remaining
records are paired by source order (handles quote-style differences at
duplicate positions like `x.dropna()` / `x.dropna().to_numpy()`).

Expression text differences are reported separately.  They do not affect
coverage counts once records are successfully paired.

**Locked baseline coverage (2026-06-04):**

| Project | AST Calls | GT Records | Missing | Stale | ExprDiff | Status |
|---------|-----------|------------|---------|-------|----------|--------|
| click1 | 5 | 5 | 0 | 0 | 1 | locked |
| flask2 | 73 | 73 | 0 | 0 | 31 | locked |
| hfhd | 444 | 444 | 0 | 0 | 65 | locked |
| Youtube | 104 | 104 | 0 | 0 | 32 | locked |
| **TOTAL** | **626** | **626** | **0** | **0** | **129** | |

All 626 AST calls are covered by GT records (multiset matching).
129 expression mismatches are benign (quote style differences between
source code and manual annotation).

### Suspicious GT Selector

The same script auto-flags GT records that need manual/dynamic verification.
It does NOT auto-change labels; review each flagged record.

**Selectors:**

| Selector | What it catches |
|----------|----------------|
| `transitive_method` | category contains "transitive_method" |
| `conversion_boundary` | category contains "conversion_boundary" |
| `expected_library_but_pcresolve_not_library` | expected_kind=library but pcresolve_kind!=library |
| `pcresolve_top_library_mismatch_expected` | pcresolve_top_library != expected_top_library |
| `manual_gt_library_call_missed_by_pcresolve` | manual_gt entries with expected_kind=library |

**Suspicious counts at lock time (2026-06-04):**

| Project | Total | Suspicious | Key Reasons |
|---------|-------|------------|-------------|
| click1 | 5 | 0 | — |
| flask2 | 73 | 26 | transitive_method=19, mismatch=7 |
| hfhd | 444 | 72 | transitive_method=62, mismatch=31, conversion_boundary=10, library_not_lib=29 |
| Youtube | 104 | 28 | transitive_method=20, mismatch=17, library_not_lib=8 |

JSON output: `verification/suspicious_selector.json`

### Dynamic Probes

Minimal standalone scripts verify receiver object ownership for high-risk
patterns.  They do NOT execute the full real project; minimal object
construction only.

**hfhd probes** (`probes/hfhd_probe.py`):

| Probe | Pattern | Conclusion |
|-------|---------|------------|
| 1 | `np.log(pd.Series).diff()` | `.diff()` receiver IS `pandas.Series`; GT label `library/pandas` is correct. PCResolve says `numpy` → **WRONG_OWNER**. |
| 2 | `df.to_numpy().T` then `.reshape()` | `.to_numpy()` is pandas API (call itself). Result is `numpy.ndarray`. `.reshape()` receiver is numpy → conversion boundary confirmed. |
| 3 | `_preaverage(...).flatten()` | `_preaverage()` operates on ndarray; `.flatten()` is numpy method. |

**Youtube probes** (`probes/youtube_probe.py`):

| Probe | Pattern | Conclusion |
|-------|---------|------------|
| 1 | `scipy.sparse.csr_matrix.todense()` | Method `__module__` is `scipy.sparse._base`. `.todense()` IS a scipy method → GT label `library/scipy` is correct. PCResolve says `python`/`local` → **MISS**. |
| 2 | `ndarray.copy()` (else branch) | `ndarray.copy()` method is numpy. GT label `library/numpy` correct. |
| 3 | `cdist(...).argmin(axis=1)` | `cdist()` returns `numpy.ndarray`. `.argmin()` is numpy method → GT label `library/numpy` is correct. PCResolve says `scipy` → **WRONG_OWNER** (inherited from cdist call). |
| 4 | `nda.mean()` | `ndarray.mean()` is numpy method. GT label `library/numpy` correct. |

Probe outputs: `verification/hfhd_probe_output.txt`, `verification/youtube_probe_output.txt`

### Human Review Views

`scripts/render_ground_truth_review.py` generates Markdown audit views from
canonical JSONL.  JSONL files in `calls/` remain the machine source of truth;
`review/` is a generated, version-controlled human audit view.  After changing
GT JSONL, rerun the render script and commit the updated review files.

```bash
python scripts/render_ground_truth_review.py              # all pilots
python scripts/render_ground_truth_review.py --project hfhd
```

**Output layout:**

```
review/
  index.md                        # aggregate pilot summary table
  <project>/
    overview.md                   # stats, kind/level/category breakdowns
    static_obvious.md             # records with verification_level=static_obvious
    static_context.md             # records with verification_level=static_context
    dynamic_probe.md              # records with verification_level=dynamic_probe
    manual_reasoned.md            # records with verification_level=manual_reasoned
    suspicious.md                 # cross-cutting: kind/owner mismatch, missing
                                  #   decorated_by, manual_reasoned/unsupported,
                                  #   ambiguous/unsupported status
```

**Suspicious criteria:**

| Criterion | What it catches |
|-----------|----------------|
| `pcresolve_kind != expected_kind` | Kind disagreement (e.g. library vs python) |
| `pcresolve_top_library != expected_top_library` and not in alternatives | Wrong owner |
| `expected_kind=library` but `pcresolve_kind!=library` | Library call classified as local/python |
| `expected_decorated_by` not subset of `pcresolve_decorated_by` | Missing decorator evidence |
| `verification_level in (manual_reasoned, unsupported)` | Needs human reasoning |
| `status in (ambiguous, unsupported)` | Beyond 1.0.5 scope |

### Verification Reports

Generated by `scripts/verify_ground_truth_calls.py --markdown`:

| File | Content |
|------|---------|
| `verification/pilot_verification_report.md` | Full human-readable report (coverage + suspicious) |
| `verification/coverage_check.json` | Machine-readable AST coverage data |
| `verification/suspicious_selector.json` | Machine-readable suspicious record list |
| `verification/hfhd_probe_output.txt` | hfhd dynamic probe output |
| `verification/youtube_probe_output.txt` | Youtube dynamic probe output |
