# recommendation — static_obvious (40 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| get_graph_030.py:13:7 | `sqlite3.connect(db_path)` | library / sqlite3 | library / sqlite3 | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:26:5 | `pd.DataFrame(scores)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:30:4 | `nx.Graph()` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:48:8 | `user_set.append(uid)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:50:8 | `venue_set.append(rid)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:54:4 | `edge_weights.append(tuple(ew))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:54:24 | `tuple(ew)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:60:0 | `nx.set_node_attributes(g, 'clus_id', node_clus)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:61:18 | `bipartite.sets(g)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:62:0 | `print('Full History Graph is graph bipartite:', nx.is_bipartite(g))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:62:48 | `nx.is_bipartite(g)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:64:0 | `pickle.dump(g, open('data/graph_objects/g.sav', 'wb'))` | library / pickle | library / pickle | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:64:15 | `open('data/graph_objects/g.sav', 'wb')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:77:5 | `pd.DataFrame(scores)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:81:4 | `nx.Graph()` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:99:8 | `user_set.append(uid)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:101:8 | `venue_set.append(rid)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:105:4 | `edge_weights.append(tuple(ew))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:105:24 | `tuple(ew)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:111:0 | `nx.set_node_attributes(g, 'clus_id', node_clus)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:112:18 | `bipartite.sets(g)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:113:0 | `print('Full History (venue clus) Graph is graph bipartite:', nx.is_...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:113:61 | `nx.is_bipartite(g)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:115:0 | `pickle.dump(g, open('data/graph_objects/g_venue.sav', 'wb'))` | library / pickle | library / pickle | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:115:15 | `open('data/graph_objects/g_venue.sav', 'wb')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:128:7 | `pd.DataFrame(tips)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:134:6 | `nx.Graph()` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:144:18 | `len(reviews)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:146:13 | `range(num_iterate)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:148:17 | `range(0, 6)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:160:16 | `user_set.append(uid)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:162:16 | `venue_set.append(rid)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:165:12 | `edge_weights.append(tuple(ew))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:165:32 | `tuple(ew)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:171:0 | `nx.set_node_attributes(rhg, 'clus_id', node_clus)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:172:18 | `bipartite.sets(rhg)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:173:0 | `print('Recent History Graph is graph bipartite:', nx.is_bipartite(r...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| get_graph_030.py:173:50 | `nx.is_bipartite(rhg)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:175:0 | `pickle.dump(rhg, open('data/graph_objects/g_recent.sav', 'wb'))` | library / pickle | library / pickle | direct_import | static_obvious | v: direct import-backed API call |
| get_graph_030.py:175:17 | `open('data/graph_objects/g_recent.sav', 'wb')` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
