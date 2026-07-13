# Deep-Graph-Kernels — dynamic_probe (1 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| Kronecker_Generator.py:105:11 | `(np.diag(W) == np.zeros(W.shape[0])).any()` | library / numpy | library / numpy | transitive_method | dynamic_probe | gt: Previously manual_gt; now collected by PCResolve<br>v: probe confirms (np.diag(W)==np.zeros(...)) returns boolean ndarray; .any() is nu |
