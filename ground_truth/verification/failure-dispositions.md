# PCResolve 1.0.5 Failure Dispositions

This report classifies every current locked primary ownership mismatch. The canonical call labels remain in `ground_truth/calls/`; the JSONL sidecar records release disposition only.

## Release Disposition

| Disposition | Records | Meaning |
|---|---:|---|
| `fix_1_0_5` | 404 | Must be closed in 1.0.5 |
| `accepted_boundary` | 4 | Documented static-analysis boundary |
| `ground_truth_correction` | 0 | Canonical GT label must be corrected |
| **Total** | **408** | |

## Repair Scope

| Repair scope | Records |
|---|---:|
| `same_scope_result_protocol` | 170 |
| `bounded_receiver_flow` | 212 |
| `conservative_identity` | 16 |
| `local_identity` | 6 |
| `documented_boundary` | 4 |
| `label_correction` | 0 |
| **Total** | **408** |

## Project Queue

| Project | Records |
|---|---:|
| `allnews` | 117 |
| `polire` | 49 |
| `MAHE_OD_DATASET` | 45 |
| `final` | 43 |
| `greenbenchmark` | 38 |
| `hfhd` | 31 |
| `political-polarisation` | 19 |
| `AIBO` | 18 |
| `simulation` | 9 |
| `scrapping` | 8 |
| `django` | 7 |
| `Contrucao` | 6 |
| `Youtube` | 6 |
| `SDOML` | 5 |
| `flask2` | 4 |
| `Python-Workshop` | 2 |
| `tensorflow1` | 1 |

## Failure Families

| Category | Records |
|---|---:|
| `transitive_method` | 81 |
| `python_protocol_method` | 69 |
| `numpy_array_receiver` | 47 |
| `builtin_string_method` | 34 |
| `torch_tensor_receiver` | 31 |
| `pandas_receiver` | 20 |
| `builtin_container_method` | 15 |
| `branch_dependent_io_receiver` | 13 |
| `conversion_boundary` | 13 |
| `matplotlib_receiver` | 12 |
| `regex_receiver` | 10 |
| `library_result_boundary` | 8 |
| `builtin_method_local_receiver` | 6 |
| `gpy_receiver` | 6 |
| `builtin` | 5 |
| `pandas_receiver_chain` | 5 |
| `android_viewclient_receiver` | 4 |
| `mapping_protocol_method` | 4 |
| `multiprocessing_receiver` | 4 |
| `box2d_receiver` | 3 |
| `local_baseline_callable` | 3 |
| `polymorphic_library_receiver` | 3 |
| `pymysql_receiver` | 3 |
| `builtin_callable` | 2 |
| `numpy_result_receiver` | 2 |
| `direct_import` | 1 |
| `dynamic_local_callable` | 1 |
| `keras_receiver` | 1 |
| `local_method` | 1 |
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
