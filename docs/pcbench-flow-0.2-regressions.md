# PCBench-driven value-flow regressions

This is a PCResolve `flow-0.2` capability report, not a rerun of VPPDetector
verdicts. The before column quotes the assessment reason in the supplied
`VPPDetector/evaluation/pcbench/results.json` snapshot (PCResolve commit
`0562220fa4565203217110c3a024b55b146aca28`). The after column describes
facts now returned by PCResolve. VPPDetector and PCART were not changed.

| PCBench case | Baseline assessment | New PCResolve fact or retained limit |
| --- | --- | --- |
| Tornado 6.0 `AsyncHTTPClient.fetch` → `HTTPRequest(...)` (A051) | `downstream_target_unresolved` | Constructor call resolves to `tornado.httpclient.HTTPRequest.__init__`, its defining location in the evaluated Tornado 6.0 source archive. |
| Tornado 3.0 `AsyncHTTPClient.__new__` → `super(AsyncHTTPClient, cls).__new__` (A052) | `downstream_target_unresolved` | Explicit `super` resolves to `tornado.util.Configurable.__new__`. |
| pandas 2.0 `DataFrame.take` (A001) | `evaluation_target_unresolved` | The inherited entry selects `pandas.core.generic.NDFrame.take`. Its ordinary `kwargs` argument to `validate_take((), kwargs)` retains the `kwargs[*]` source. |
| pandas 2.0 `Series.take` (A003) | `indirect_parameter_transformation` | The ordinary mapping argument retains `kwargs[*]`; validation policy remains outside PCResolve. |
| aiohttp 0.8.2 `BaseConnector.__init__` (A004) | `pcresolve_source_unavailable` | `self.*` assignment boundaries identify `self` and other parameters, not `kwargs`. Import-reachable parse failures remain `unknown`, but list the syntactically unread `kwargs` parameter in `unaffected_values`; unrelated failed files report `entry_relation=unrelated`. |
| Keras 2.1.6 `ReduceLROnPlateau` (A002) | `variadic_capture_mutated` | `kwargs["epsilon"]` membership and pop are element-specific; the subsequent assignment boundary retains the `kwargs["epsilon"]` root. Rename/compatibility judgment remains downstream. |
| Dask 2022.4.2 `read_parquet` (A007) | `variadic_capture_mutated` | Conditional `kwargs.pop("gather_statistics")` reports a bounded conditional removal with branch conditions. |
| Matplotlib 3.6/3.7 `FancyArrowPatch`/`FancyBboxPatch` (A014/A015) | `variadic_capture_mutated` / `downstream_target_unresolved` | `super().__init__` selects the `Patch.__init__` source candidate, accompanied by decorator boundaries; it is not claimed as a definite runtime callee. |
| Matplotlib 3.5 `Shadow` (A016) | `pcresolve_unsupported_assignment` | `self.update` selects the inherited `Artist.update` source candidate; decorated class/caller boundaries remain. |
| Matplotlib 3.7 `Colorbar.set_ticks` (A013) | `downstream_target_unresolved` | `self._long_axis().set_ticks` remains unresolved because the returned axis receiver has no proved local nominal type. |
| Pydantic 1.5 `create_model(model_name=...)` (A020) | `old_argument_not_forwarded` (`SAFE` in the old VPP snapshot) | Binding reports `model_name` captured by `**field_definitions` and required `__model_name` missing; `binding_status=invalid`. PCResolve does not assign a compatibility verdict. |

The synthetic fixtures under `tests/fixtures/value_flow_enhancements/` exercise
each mechanism independently before the corresponding real-source regressions
in `tests/test_pcbench_real_sources.py`. Real tests use the hash-checked source
inventory when available and otherwise skip. The originally supplied path
`evaluation/pcbench/run/_evaluation.py` was absent in the local VPPDetector
checkout; its available evaluator is `evaluation/pcbench/run_evaluation.py`.

The output additions are documented in [the contract](output-contract.md) and
[value-flow semantics](value-flow.md). Stable ownership `schema_version=1.0`
is unchanged. The old VPP `SAFE`/`UNKNOWN`/`MUST_FAIL` counts are not updated
by these PCResolve-only tests; integration requires a separate VPPDetector run.
