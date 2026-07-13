# Contrucao — static_context (3 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| main.py:41:9 | `filtro(texts)` | library / spacy | library / spacy | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| main.py:125:0 | `tfidfDataFrame.drop([0], inplace=True)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .drop( method on pandas Series/DataFrame |
| main.py:126:0 | `tfidfDataFrame.set_axis(vocabulario, axis='columns', inplace=True)` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
