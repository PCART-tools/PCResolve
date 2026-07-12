# Deep-Graph-Kernels — manual_reasoned (3 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| Kronecker_Generator.py:102:8 | `Parameter.checkInt(k, 1, float('inf'))` | unknown / unknown | unknown / unknown | transitive_method | manual_reasoned | v: outer receiver Parameter is unresolved; unknown owner manually confirmed |
| Kronecker_Generator.py:105:11 | `(np.diag(W)==np.zeros(W.shape[0])).any()` | library / numpy |  /  | transitive_method | manual_reasoned | gt: PCResolve missed: .any() on Compare (BinOp comparison) receiver; ast.Compare rec<br>v: manual_gt: .any() on comparison-expression receiver; ast.Compare not handled in  |
| Kronecker_Generator.py:118:8 | `Parameter.checkInt(k, 1, float('inf'))` | unknown / unknown | unknown / unknown | transitive_method | manual_reasoned | v: outer receiver Parameter is unresolved; unknown owner manually confirmed |
