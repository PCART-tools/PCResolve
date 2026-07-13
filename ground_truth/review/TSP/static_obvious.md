# TSP — static_obvious (18 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| ctfds.py:7:12 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:10:18 | `nx.minimum_spanning_tree(graph)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:13:20 | `nx.degree(minSpanTree)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:17:24 | `nx.subgraph(graph, oddDegreeVertices)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:20:24 | `list(nx.min_weight_matching(oddVertexSubgraph, maxcardinality=True))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| ctfds.py:20:29 | `nx.min_weight_matching(oddVertexSubgraph, maxcardinality=True)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:23:20 | `nx.MultiGraph(minSpanTree)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:28:22 | `list(nx.eulerian_circuit(combinedGraph, source=1))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| ctfds.py:28:27 | `nx.eulerian_circuit(combinedGraph, source=1)` | library / networkx | library / networkx | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:30:14 | `set()` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| ctfds.py:37:12 | `visited.add(u)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| ctfds.py:38:15 | `len(hamiltonianPath)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| ctfds.py:45:10 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:52:14 | `tsplib95.load('lib/eil51.tsp')` | library / tsplib95 | library / tsplib95 | direct_import | static_obvious | v: direct import-backed API call |
| ctfds.py:56:34 | `christofides(graph)` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| ctfds.py:57:4 | `print('Peso total:', weight)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| ctfds.py:58:4 | `print('Caminho:', path)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| ctfds.py:59:4 | `print('Tempo de execução:', executionTime)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
