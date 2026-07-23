# PCResolve 1.0.5 Failure Dispositions

This report classifies every current locked primary ownership mismatch. The canonical call labels remain in `ground_truth/calls/`; the JSONL sidecar records release disposition only.

## Release Disposition

| Disposition | Records | Meaning |
|---|---:|---|
| `fix_1_0_5` | 355 | Must be closed in 1.0.5 |
| `accepted_boundary` | 4 | Documented static-analysis boundary |
| `ground_truth_correction` | 0 | Canonical GT label must be corrected |
| **Total** | **359** | |

## Repair Scope

| Repair scope | Records |
|---|---:|
| `same_scope_result_protocol` | 153 |
| `bounded_receiver_flow` | 187 |
| `conservative_identity` | 7 |
| `local_identity` | 8 |
| `documented_boundary` | 4 |
| `label_correction` | 0 |
| **Total** | **359** |

## Project Queue

| Project | Records |
|---|---:|
| `allnews` | 104 |
| `polire` | 46 |
| `MAHE_OD_DATASET` | 38 |
| `greenbenchmark` | 38 |
| `hfhd` | 31 |
| `final` | 25 |
| `political-polarisation` | 19 |
| `AIBO` | 17 |
| `scrapping` | 8 |
| `django` | 7 |
| `Contrucao` | 6 |
| `Youtube` | 6 |
| `SDOML` | 5 |
| `flask2` | 4 |
| `Python-Workshop` | 2 |
| `simulation` | 2 |
| `tensorflow1` | 1 |

## Failure Families

| Category | Records |
|---|---:|
| `python_protocol_method` | 65 |
| `transitive_method` | 56 |
| `numpy_array_receiver` | 47 |
| `torch_tensor_receiver` | 31 |
| `builtin_string_method` | 30 |
| `pandas_receiver` | 20 |
| `conversion_boundary` | 13 |
| `matplotlib_receiver` | 12 |
| `builtin_container_method` | 11 |
| `library_result_boundary` | 8 |
| `regex_receiver` | 8 |
| `branch_dependent_io_receiver` | 7 |
| `builtin_method_local_receiver` | 6 |
| `gpy_receiver` | 6 |
| `pandas_receiver_chain` | 5 |
| `android_viewclient_receiver` | 4 |
| `builtin` | 4 |
| `mapping_protocol_method` | 4 |
| `multiprocessing_receiver` | 4 |
| `box2d_receiver` | 3 |
| `local_baseline_callable` | 3 |
| `pymysql_receiver` | 3 |
| `local_method` | 2 |
| `numpy_result_receiver` | 2 |
| `direct_import` | 1 |
| `dynamic_local_callable` | 1 |
| `keras_receiver` | 1 |
| `local_call` | 1 |
| `monkey_patched_local_method` | 1 |

## Boundary And Label Records

| Disposition | Location | Expression | Reason |
|---|---|---|---|
| `accepted_boundary` | `flask2/app.py:66:27` | `request.json.get('description', '')` | framework payload mapping protocol boundary |
| `accepted_boundary` | `flask2/app.py:83:24` | `request.json.get('title', task['title'])` | framework payload mapping protocol boundary |
| `accepted_boundary` | `flask2/app.py:84:30` | `request.json.get('description', task['description'])` | framework payload mapping protocol boundary |
| `accepted_boundary` | `flask2/app.py:85:23` | `request.json.get('done', task['done'])` | framework payload mapping protocol boundary |

## Release Rule

1. Every `fix_1_0_5` entry must either become a primary hit or be reclassified with reviewed evidence.
2. `accepted_boundary` entries remain visible in the release report.
3. `ground_truth_correction` entries must update the canonical GT before algorithm work continues.
4. No mismatch may remain without a disposition.
