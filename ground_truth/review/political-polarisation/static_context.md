# political-polarisation — static_context (12 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| analyze_hashtag.py:27:14 | `df_name.str.split(',', expand=True)` | unknown / unknown | unknown / unknown | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:63:12 | `dg.add_edge(username, mention.strip())` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:63:34 | `mention.strip()` | unknown / unknown | unknown / unknown | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:75:30 | `dg.subgraph(largest_component)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:94:13 | `all_df.dropna(how='any', subset=['hashtag'])` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .dropna( method on pandas Series/DataFrame |
| analyze_hashtag.py:94:13 | `all_df.dropna(how='any', subset=['hashtag']).drop(columns=['lang'])` | library / pandas | library / pandas | transitive_method | static_context | v: pandas .dropna( method on pandas Series/DataFrame |
| analyze_hashtag.py:95:4 | `all_df['is_retweet'].astype('bool')` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:96:4 | `all_df['is_quote'].astype('bool')` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:97:4 | `all_df['hashtag'].astype('string')` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:98:24 | `all_df['hashtag'].map(lambda x: clean_list(x))` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:99:4 | `all_df['mentions'].astype('string')` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| analyze_hashtag.py:100:25 | `all_df['mentions'].map(lambda x: clean_list(x))` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
