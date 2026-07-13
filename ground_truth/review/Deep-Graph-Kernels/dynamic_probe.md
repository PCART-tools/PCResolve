# Deep-Graph-Kernels — dynamic_probe (1 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| Kronecker_Generator.py:105:11 | `(np.diag(W)==np.zeros(W.shape[0])).any()` | library / numpy |  /  | transitive_method | dynamic_probe | gt: PCResolve missed: .any() on Compare receiver; ast.Compare receiver is not handle<br>v: probe: type(comparison_result) is numpy.ndarray; comparison_result.any.__self__  |
