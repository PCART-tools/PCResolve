# Youtube — static_context (14 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| FuunyClusters.py:44:4 | `allseeds.append(tuple(model[word]))` | python / python | python / python | builtin_method_local_receiver | static_context | gt: builtin append() on local container<br>v: builtin list method on local container; receiver is local list literal or variab |
| FuunyClusters.py:45:4 | `words.append(word)` | python / python | python / python | builtin_method_local_receiver | static_context | gt: builtin append() on local container<br>v: builtin list method on local container; receiver is local list literal or variab |
| FuunyClusters.py:108:18 | `allseeds.index(tuple(c))` | python / python | python / python | builtin_method_local_receiver | static_context | gt: builtin index() on local container<br>v: builtin list method on local container; receiver is local list literal or variab |
| FuunyClusters.py:109:22 | `Rseeds.index(c)` | python / python | python / python | builtin_method_local_receiver | static_context | gt: builtin list.index()<br>v: builtin list method on local container; receiver is local list literal or variab |
| FuunyClusters.py:122:8 | `distPartDict[i[1]].append(i[0])` | python / python | python / python | builtin_method_local_receiver | static_context | gt: list.append on defaultdict list<br>v: builtin list method on local container; receiver is local list literal or variab |
| FuunyClusters.py:133:8 | `temp.extend((tuple(n) for n in newSeeds))` | python / python | python / python | builtin_method_local_receiver | static_context | gt: builtin extend() on local container<br>v: builtin list method on local container; receiver is local list literal or variab |
| FuunyClusters.py:135:33 | `allseeds.index(tuple(cent))` | python / python | python / python | builtin_method_local_receiver | static_context | gt: builtin index() on local container<br>v: builtin list method on local container; receiver is local list literal or variab |
| FuunyClusters.py:137:27 | `allseeds.index(tuple(new))` | python / python | python / python | builtin_method_local_receiver | static_context | gt: builtin index() on local container<br>v: builtin list method on local container; receiver is local list literal or variab |
| FuunyClusters.py:140:8 | `my_prbar.update()` | library / pyprind | library / pyprind | transitive_method | static_context | v: receiver ownership inferred from pyprind.ProgBar() return |
| FuunyClusters.py:145:23 | `allseeds.index(tuple(n))` | python / python | python / python | builtin_method_local_receiver | static_context | gt: builtin index() on local container<br>v: builtin list method on local container; receiver is local list literal or variab |
| Kmeans.py:28:13 | `centres.copy()` | library / numpy | local / local | transitive_method | static_context | gt: numpy .copy()<br>v: numpy .copy( method on numpy ndarray |
| Kmeans.py:39:15 | `D.argmin(axis=1)` | library / numpy | unknown / unknown | transitive_method | static_context | gt: numpy .argmin() on array<br>v: .argmin() on numpy ndarray |
| Kmeans.py:41:17 | `distances.mean()` | library / numpy | unknown / unknown | transitive_method | static_context | gt: numpy .mean() on array<br>v: numpy .mean( method on numpy ndarray |
| Kmeans.py:49:30 | `X[c].mean(axis=0)` | library / numpy | library / numpy | transitive_method | static_context | v: numpy .mean( method on numpy ndarray |
