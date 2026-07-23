# political-polarisation — static_obvious (38 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| analyze_hashtag.py:8:0 | `pd.set_option('display.max_rows', 10)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:9:0 | `pd.set_option('display.max_columns', 10)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:10:0 | `pd.set_option('expand_frame_repr', False)` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:39:4 | `print({k: v for (k, v) in sorted(word_count.items(), key=lambda ite...` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:39:28 | `sorted(word_count.items(), key=lambda item: item[1], reverse=True)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:40:16 | `WordCloud(width=800, height=800, background_color='white', stopword...` | library / wordcloud | library / wordcloud | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:40:16 | `WordCloud(width=800, height=800, background_color='white', stopword...` | library / wordcloud | library / wordcloud | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:42:36 | `set(STOPWORDS)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:43:53 | `' '.join(df_name)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:45:4 | `plt.figure(figsize=(8, 8), facecolor=None)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:46:4 | `plt.imshow(wordcloud)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:47:4 | `plt.axis('off')` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:48:4 | `plt.tight_layout(pad=0)` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:49:4 | `plt.show()` | library / matplotlib | library / matplotlib | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:58:9 | `nx.Graph()` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:59:18 | `df.iterrows()` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:68:12 | `print(count)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:74:24 | `max(nx.connected_components(dg), key=len)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:74:28 | `nx.connected_components(dg)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:76:4 | `print(nx.number_of_nodes(largest_component_graph))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:76:10 | `nx.number_of_nodes(largest_component_graph)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:77:16 | `nx.community.kernighan_lin_bisection(largest_component_graph, max_i...` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:78:4 | `print(len(biparties))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:78:10 | `len(biparties)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:79:24 | `nx.community.label_propagation_communities(largest_component_graph)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:80:24 | `sorted(label_communities, key=lambda i: len(i), reverse=True)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:80:64 | `len(i)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:81:4 | `print(len(label_communities))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:81:10 | `len(label_communities)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:87:25 | `nx.algorithms.community.greedy_modularity_communities(largest_compo...` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:88:4 | `print(len(greedy_communities))` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:88:10 | `len(greedy_communities)` | python / python | python / python | builtin | static_obvious | v: Python builtin function call |
| analyze_hashtag.py:92:13 | `pd.read_csv('./data_cleaned/tweets/out_3143_small.csv', delimiter='...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:92:13 | `pd.read_csv('./data_cleaned/tweets/out_3143_small.csv', delimiter='...` | library / pandas | library / pandas | direct_import | static_obvious | v: direct import-backed API call |
| analyze_hashtag.py:98:56 | `clean_list(x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| analyze_hashtag.py:100:58 | `clean_list(x)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| analyze_hashtag.py:103:4 | `build_mention_graph(all_df)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| analyze_hashtag.py:104:4 | `display(all_df)` | library / IPython | library / IPython | direct_import | static_obvious | v: direct import-backed API call |
