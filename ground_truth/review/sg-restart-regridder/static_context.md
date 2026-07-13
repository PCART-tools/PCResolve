# sg-restart-regridder — static_context (4 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| experiments_table.py:36:15 | `df['SF'].map('{:> 4.1f}'.format)` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| experiments_table.py:37:17 | `df['Lat0'].map('{: 4.1f}'.format)` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| experiments_table.py:38:17 | `df['Lon0'].map('{: 5.1f}'.format)` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| experiments_table.py:40:12 | `df.to_latex(index_names=True, multirow=True, col_space=0)` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
