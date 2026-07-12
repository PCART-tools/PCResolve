# Deep-Graph-Kernels — Suspicious Records (1)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| Kronecker_Generator.py:105:11 | `(np.diag(W)==np.zeros(W.shape[0])).any()` | library / numpy |  /  | transitive_method | manual_reasoned | manual_gt<br>pcresolve missing candidate: expected=library/numpy<br>verification_level=manual_reasoned |
