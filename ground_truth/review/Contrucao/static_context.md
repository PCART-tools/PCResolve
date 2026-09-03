# Contrucao — static_context (9 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| main.py:18:9 | `letra.isalpha()` | python / python | python / python | builtin_string_method | static_context | gt: callable is inherited from the builtin str type<br>v: receiver follows project-local string construction, split, or iteration |
| main.py:19:18 | `palavra.replace(letra, '')` | python / python | python / python | builtin_string_method | static_context | gt: callable is inherited from the builtin str type<br>v: receiver follows project-local string construction, split, or iteration |
| main.py:41:9 | `filtro(texts)` | library / spacy | library / spacy | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| main.py:50:17 | `sentence.split()` | python / python | python / python | builtin_string_method | static_context | gt: callable is inherited from the builtin str type<br>v: receiver follows project-local string construction, split, or iteration |
| main.py:51:29 | `palavra.strip()` | python / python | python / python | builtin_string_method | static_context | gt: callable is inherited from the builtin str type<br>v: receiver follows project-local string construction, split, or iteration |
| main.py:73:17 | `sentence.split()` | python / python | python / python | builtin_string_method | static_context | gt: callable is inherited from the builtin str type<br>v: receiver follows project-local string construction, split, or iteration |
| main.py:74:27 | `palavra.strip()` | python / python | python / python | builtin_string_method | static_context | gt: callable is inherited from the builtin str type<br>v: receiver follows project-local string construction, split, or iteration |
| main.py:125:0 | `tfidfDataFrame.drop([0], inplace=True)` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .drop( method on pandas Series/DataFrame |
| main.py:126:0 | `tfidfDataFrame.set_axis(vocabulario, axis='columns', inplace=True)` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
