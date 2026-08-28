# PCResolve 1.0.5 Failure Dispositions

This report classifies every current locked primary ownership mismatch. The canonical call labels remain in `ground_truth/calls/`; the JSONL sidecar records release disposition only.

## Classification Policy

Ground truth records semantic or runtime ownership. Release disposition asks a different question: whether that exact owner is recoverable from project source under the 1.0.5 pure-static contract.

1. `static_obvious` and `static_context` evidence remains in the exact-owner repair queue.
2. A runtime-only owner with a current `unknown` result is accepted as an honest static boundary and remains a scored GT miss.
3. A runtime-only owner with a current `local` or library result must first drop that unsupported certainty to `unknown`.
4. No library-name or external return-type whitelist is introduced to turn runtime observations into static guesses.

## Release Disposition

| Disposition | Records | Meaning |
|---|---:|---|
| `fix_1_0_5` | 186 | Must be closed in 1.0.5 |
| `accepted_unknown` | 63 | Current unknown is justified by the static evidence boundary |
| `ground_truth_correction` | 0 | Canonical GT label must be corrected |
| **Total** | **249** | |

## Repair Scope

| Repair scope | Records |
|---|---:|
| `same_scope_result_protocol` | 76 |
| `bounded_receiver_flow` | 101 |
| `conservative_identity` | 8 |
| `local_identity` | 1 |
| `evidence_limited_unknown` | 63 |
| `label_correction` | 0 |
| **Total** | **249** |

## Evidence Boundary

| Verification level | Disposition | Records |
|---|---|---:|
| `dynamic_probe` | `accepted_unknown` | 54 |
| `dynamic_probe` | `fix_1_0_5` | 4 |
| `manual_reasoned` | `accepted_unknown` | 8 |
| `static_context` | `accepted_unknown` | 1 |
| `static_context` | `fix_1_0_5` | 182 |

## Project Queue

| Project | Records |
|---|---:|
| `allnews` | 52 |
| `MAHE_OD_DATASET` | 29 |
| `greenbenchmark` | 28 |
| `hfhd` | 26 |
| `polire` | 26 |
| `final` | 25 |
| `political-polarisation` | 21 |
| `AIBO` | 11 |
| `scrapping` | 8 |
| `django` | 7 |
| `Youtube` | 6 |
| `flask2` | 4 |
| `Python-Workshop` | 2 |
| `simulation` | 2 |
| `Contrucao` | 1 |
| `tensorflow1` | 1 |

## Failure Families

| Category | Records |
|---|---:|
| `transitive_method` | 50 |
| `python_protocol_method` | 46 |
| `numpy_array_receiver` | 28 |
| `torch_tensor_receiver` | 26 |
| `builtin_string_method` | 17 |
| `matplotlib_receiver` | 11 |
| `pandas_receiver` | 10 |
| `conversion_boundary` | 9 |
| `library_result_boundary` | 9 |
| `gpy_receiver` | 5 |
| `pandas_receiver_chain` | 5 |
| `android_viewclient_receiver` | 4 |
| `builtin_container_method` | 4 |
| `builtin_method_local_receiver` | 4 |
| `local_call` | 4 |
| `mapping_protocol_method` | 4 |
| `direct_import` | 3 |
| `box2d_receiver` | 2 |
| `builtin` | 2 |
| `numpy_result_receiver` | 2 |
| `dynamic_local_callable` | 1 |
| `keras_receiver` | 1 |
| `local_method` | 1 |
| `monkey_patched_local_method` | 1 |

## Unknown Outcome Queue

These records either already have a justified `unknown` result or must drop a source-unsupported `local`/library claim to `unknown`.

| Project | Category | Disposition | Records |
|---|---|---|---:|
| `AIBO` | `dynamic_local_callable` | `accepted_unknown` | 1 |
| `AIBO` | `monkey_patched_local_method` | `accepted_unknown` | 1 |
| `Contrucao` | `library_result_boundary` | `accepted_unknown` | 1 |
| `Python-Workshop` | `transitive_method` | `accepted_unknown` | 2 |
| `Youtube` | `transitive_method` | `accepted_unknown` | 4 |
| `django` | `builtin_method_local_receiver` | `accepted_unknown` | 1 |
| `django` | `builtin_method_local_receiver` | `fix_1_0_5` | 2 |
| `django` | `transitive_method` | `accepted_unknown` | 4 |
| `final` | `builtin_method_local_receiver` | `accepted_unknown` | 1 |
| `final` | `direct_import` | `accepted_unknown` | 1 |
| `final` | `transitive_method` | `accepted_unknown` | 23 |
| `flask2` | `mapping_protocol_method` | `fix_1_0_5` | 4 |
| `hfhd` | `conversion_boundary` | `accepted_unknown` | 7 |
| `hfhd` | `local_call` | `accepted_unknown` | 4 |
| `hfhd` | `transitive_method` | `accepted_unknown` | 3 |
| `political-polarisation` | `direct_import` | `accepted_unknown` | 2 |
| `scrapping` | `library_result_boundary` | `accepted_unknown` | 8 |
| `simulation` | `conversion_boundary` | `fix_1_0_5` | 2 |

## Ground Truth Corrections

| Location | Expression | Reason |
|---|---|---|
| - | - | None in the current locked GT |

## Release Rule

1. Every `fix_1_0_5` entry must either become a primary hit or be reclassified with reviewed evidence.
2. `accepted_unknown` entries remain scored as GT misses, but do not require a guessed exact owner for release.
3. `ground_truth_correction` entries must update the canonical GT before algorithm work continues.
4. No mismatch may remain without a disposition.
