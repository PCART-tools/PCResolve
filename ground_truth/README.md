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
  "annotation_status": "reviewed",
  "category": "decorated_callable_receiver",
  "notes": ""
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
  "annotation_status": "reviewed",
  "category": "",
  "notes": "missed by PCResolve"
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

`pcresolve_*` fields are pre-filled by the candidate generator as
seed data; they are never truth.  For `source="manual_gt"` entries
they are present but empty.  Evaluators must read all `pcresolve_*`
fields with `.get()` or equivalent tolerant access.

### `expected_kind` Values

| Value | Meaning | Example owners |
|-------|---------|---------------|
| `library` | Import-backed library owner | `requests`, `numpy`, `flask`, `json`, `pathlib`, `csv`, `re` |
| `python` | Builtin / Python-provided API / builtin object method | `len()`, `open()`, `str.strip()`, `list.append()` |
| `local` | Project-defined callable or object | `make_session()`, `self.helper()` |
| `unknown` | Cannot be determined statically | dynamic lookup, unresolved receiver |

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

| Project | Rationale | Labeling Focus |
|---------|-----------|----------------|
| `click1` | Small, clean boundaries | Decorators, decorated callable receivers |
| `flask2` | Small, web factory pattern | Local factory, test client, context/receiver |
| `hfhd` | Pandas/NumPy dense | Conversion boundary, method chaining, RHS/LHS |
| `Youtube` | List/iteration + scientific | Container contamination, NumPy/SciPy ownership |
| `AIBO` | Large project stress test | Scale, FP/FN classification |
| `allnews` | Large NLP/ML project | NER, WikiExtractor, performance at scale |
