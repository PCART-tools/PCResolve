# Deep-Graph-Kernels — static_context (8 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| Kronecker_Generator.py:23:0 | `A1.setdiag(rand(100))` | library / scipy | library / scipy | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| Kronecker_Generator.py:25:5 | `A1.tocsr()` | library / scipy | library / scipy | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| Kronecker_Generator.py:31:0 | `B1.setdiag(rand(100))` | library / scipy | library / scipy | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| Kronecker_Generator.py:33:5 | `B1.tocsr()` | library / scipy | library / scipy | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| Kronecker_Generator.py:135:8 | `graph.setWeightMatrix(Wi)` | library / apgl | library / apgl | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| Kronecker_Generator.py:150:8 | `initialGraph.addEdge(0, 1)` | library / apgl | library / apgl | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| Kronecker_Generator.py:151:8 | `initialGraph.addEdge(1, 2)` | library / apgl | library / apgl | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| Kronecker_Generator.py:154:12 | `initialGraph.addEdge(i, i)` | library / apgl | library / apgl | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
