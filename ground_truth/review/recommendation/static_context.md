# recommendation — static_context (20 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| get_graph_030.py:14:4 | `conn.cursor()` | library / sqlite3 | library / sqlite3 | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:19:0 | `c.execute('SELECT combined_clus_id as clus_id, t.uid, t.rid, avg(se...` | library / sqlite3 | library / sqlite3 | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:23:9 | `c.fetchall()` | library / sqlite3 | library / sqlite3 | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:37:11 | `df.iterrows()` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:56:0 | `g.add_nodes_from(user_set, bipartite=0)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:57:0 | `g.add_nodes_from(venue_set, bipartite=1)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:58:0 | `g.add_weighted_edges_from(edge_weights)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:70:0 | `c.execute('SELECT senti_clus_id as clus_id, t.uid, t.rid, avg(senti...` | library / sqlite3 | library / sqlite3 | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:74:9 | `c.fetchall()` | library / sqlite3 | library / sqlite3 | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:88:11 | `df.iterrows()` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:107:0 | `g.add_nodes_from(user_set, bipartite=0)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:108:0 | `g.add_nodes_from(venue_set, bipartite=1)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:109:0 | `g.add_weighted_edges_from(edge_weights)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:121:0 | `c.execute('SELECT u.combined_clus_id, t.uid,t.rid,t.created_at,sent...` | library / sqlite3 | library / sqlite3 | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:127:7 | `c.fetchall()` | library / sqlite3 | library / sqlite3 | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:131:8 | `t_df.groupby('uid')` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:141:11 | `gt_df.groups.items()` | library / pandas | library / pandas | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:167:0 | `rhg.add_nodes_from(user_set, bipartite=0)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:168:0 | `rhg.add_nodes_from(venue_set, bipartite=1)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
| get_graph_030.py:169:0 | `rhg.add_weighted_edges_from(edge_weights)` | library / networkx | library / networkx | transitive_method | static_context | v: transitive method; receiver ownership inferred through return-value propagation  |
