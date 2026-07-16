# TSP — dynamic_probe (3 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| ctfds.py:36:12 | `hamiltonianPath.append(u)` | python / python | python / python | builtin_method_local_receiver | dynamic_probe | v: runtime probe: receiver type is builtins.list; append is bound to the list and i |
| ctfds.py:42:4 | `hamiltonianPath.append(hamiltonianPath[0])` | python / python | python / python | builtin_method_local_receiver | dynamic_probe | v: runtime probe: receiver type is builtins.list; append is bound to the list and i |
| ctfds.py:53:12 | `problem.get_graph()` | library / tsplib95 | library / tsplib95 | transitive_method | dynamic_probe | v: runtime probe: inspect.getmodule(problem.get_graph) resolves to tsplib95.models |
