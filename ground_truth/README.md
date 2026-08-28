# PCResolve 1.0.5 Ground Truth Evaluation

Real-project ground truth for evaluating PCResolve's library API
call ownership accuracy (recall, precision, ownership accuracy).

## Scope

We evaluate **call-site classification**: given a call expression in a
Python file, does PCResolve correctly identify:

1. The call's `expected_kind` (library / python / local / unknown)
2. Which top-level library it belongs to (`top_library`)
3. Auxiliary evidence (`alternatives`, `decorated_by`)

Standalone symbol provenance and library usage aggregation are out of scope
for 1.0.5 scoring. Bounded inter-procedural evidence is used when it changes
call-site ownership.

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
| `auto_labeled` | Mechanically labeled by high-confidence rules (DIRECT_IMPORT, BUILTIN, bare local definition, decorated local callable). Not human-reviewed and not lock-ready. |
| `draft` | Initial labeling; `expected_*` and `status` may be empty. |
| `reviewed` | Reviewed by a second annotator. All required fields populated. |
| `locked` | Finalized. No further changes without schema version bump. |

Draft projects may mix `draft` and `auto_labeled` records.  Both must
be converted to `reviewed` before the project can be locked.
`add_verification_levels.py --check` rejects anything other than
uniform `reviewed` or `locked`.

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
| `annotation_status` | yes | `auto_labeled`, `draft`, `reviewed`, or `locked` |
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

## Locked Evaluation Set

All 42 fixture projects are **locked** (2026-07-20). The set contains
5,788 call records with 0 missing and 0 stale records. The current analyzer
snapshot has 5,541 primary hits and 247 primary misses, for aggregate recall
0.957. AST call coverage is 5,788/5,788.

Evidence is distributed across 3,738 `static_obvious`, 1,815
`static_context`, 185 `dynamic_probe`, and 50 `manual_reasoned` records.
The generated [review index](review/README.md) is the authoritative current
per-project breakdown.

### Repair Priority

The 408 records in generated `suspicious.md` views form the current repair
queue. They include known inter-procedural boundaries as well as statically
actionable ownership gaps. Release triage must use the current views instead
of the earlier pilot-only miss counts.

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

**Known builtin container method.** `module_list.append(...)`,
`local_list.append(...)`, `allseeds.index(...)`, and
`defaultdict(list)[k].append(...)` use `expected_kind="python"` and
`expected_top_library="python"`. The lexical scope and application
purpose do not change the callable owner. An explicit list binding in
a function still exposes Python's `list.append`. Scope-aware container
metadata prevents a same-name project-local object from inheriting this
classification. An unresolved receiver is not promoted by method name
alone.

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

**Locked baseline coverage (2026-07-20):** all 5,788 AST calls are covered by
5,788 GT records. There are 0 missing and 0 stale records. Expression text
differences are reported separately and do not affect position-based
multiset matching.

### Suspicious GT Selector

The same script auto-flags GT records that need manual/dynamic verification.
It does NOT auto-change labels; review each flagged record.

`suspicious.md` contains only GT versus PCResolve mismatches, including kind,
primary owner, alternatives, decorated evidence, and missing candidates.
Records are not included merely because they use contextual or dynamic
evidence. The current locked set contains 408 suspicious records.

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
| 4 | NumPy ufunc + pandas preservation matrix | `np.{log,exp,sqrt,abs}` applied to `pd.Series`/`pd.DataFrame` preserve the pandas receiver type. `.diff()`/`.mean()`/`.dropna()` bound method owner is pandas. Validates `_RECEIVER_PRESERVE_UFUNCS` static rule. |
| 5 | Negative conversion matrix | `np.array(pd.Series)`, `np.asarray(pd.Series)`, `pd.Series.to_numpy()`, `pd.Series.values` all return `numpy.ndarray`. `.reshape()`/`.flatten()` bound method owner is numpy, NOT pandas. Validates `_CONVERSION_METHOD_TARGETS` and `_CONVERSION_ATTRIBUTE_TARGETS`. |

NumPy ufunc preservation matrix validates log/exp/sqrt/abs on pandas Series/DataFrame; conversion matrix validates array/asarray/to_numpy/values return ndarray.

**Youtube probes** (`probes/youtube_probe.py`):

| Probe | Pattern | Conclusion |
|-------|---------|------------|
| 1 | `scipy.sparse.csr_matrix.todense()` | Method `__module__` is `scipy.sparse._base`. `.todense()` IS a scipy method → GT label `library/scipy` is correct. PCResolve says `python`/`local` → **MISS**. |
| 2 | `ndarray.copy()` (else branch) | `ndarray.copy()` method is numpy. GT label `library/numpy` correct. |
| 3 | `cdist(...).argmin(axis=1)` | `cdist()` returns `numpy.ndarray`. `.argmin()` is numpy method → GT label `library/numpy` is correct. PCResolve says `scipy` → **WRONG_OWNER** (inherited from cdist call). |
| 4 | `nda.mean()` | `ndarray.mean()` is numpy method. GT label `library/numpy` correct. |

Probe outputs: `verification/hfhd_probe_output.txt`, `verification/youtube_probe_output.txt`

**scrapping probe** (`probes/scrapping_probe.py`):

The probe separates callable ownership from result ownership for
`Tag.get("href")`.  `Tag.get` belongs to `bs4`, while a normal `href` value is
a builtin `str`, so the following `link.find(...)` call belongs to `python`.

Probe output: `verification/scrapping_probe_output.txt`

**Round 6 probes** (`probes/round6_probe.py`):

The consolidated probe covers the reviewed receiver boundaries in TSP,
SDOML, Python-Workshop, simulation, and final. It verifies builtin list/string
methods, NumPy arrays and `poly1d` results, Pandas DataFrame/Series/GroupBy and
plot accessors, skimage conversion results, tsplib95 problem methods, and
PorePy grid receivers. Optional libraries are reported as `SKIP` when they are
not installed; installed libraries must satisfy the ownership assertions.

```bash
python ground_truth/probes/round6_probe.py
```

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
  README.md                       # pilot summary table (entry point)
  <project>/
    README.md                      # stats, kind/level/category breakdowns
    static_obvious.md             # records with verification_level=static_obvious
    static_context.md             # records with verification_level=static_context
    dynamic_probe.md              # records with verification_level=dynamic_probe
    manual_reasoned.md            # records with verification_level=manual_reasoned
    needs_annotation.md           # records awaiting GT annotation (no verif. level)
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
| `verification_level=unsupported` | Beyond the supported evaluation contract |
| `status in (ambiguous, unsupported)` | Beyond 1.0.5 scope |

Matched `manual_reasoned` records remain visible in their evidence view but
are not suspicious solely because of their verification level.

### Verification Reports

Generated by `scripts/verify_ground_truth_calls.py --markdown`:

| File | Content |
|------|---------|
| `verification/failure-analysis.md` | Current 42-project mismatch taxonomy and root-cause analysis |
| `verification/pilot_verification_report.md` | Full human-readable report (coverage + suspicious) |
| `verification/coverage_check.json` | Machine-readable AST coverage data |
| `verification/suspicious_selector.json` | Machine-readable suspicious record list |
| `verification/hfhd_probe_output.txt` | hfhd dynamic probe output |
| `verification/youtube_probe_output.txt` | Youtube dynamic probe output |
