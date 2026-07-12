# Youtube — Suspicious Records (17)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| FuunyClusters.py:44:4 | `allseeds.append(tuple(model[word]))` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| FuunyClusters.py:45:4 | `words.append(word)` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| FuunyClusters.py:108:18 | `allseeds.index(tuple(c))` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| FuunyClusters.py:122:8 | `distPartDict[i[1]].append(i[0])` | python / python | library / collections | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=library<br>owner mismatch: expected=python pcresolve=collections |
| FuunyClusters.py:133:8 | `temp.extend((tuple(n) for n in newSeeds))` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| FuunyClusters.py:135:33 | `allseeds.index(tuple(cent))` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| FuunyClusters.py:137:27 | `allseeds.index(tuple(new))` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| FuunyClusters.py:145:23 | `allseeds.index(tuple(n))` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| Kmeans.py:27:14 | `centres.todense()` | library / scipy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=scipy pcresolve=local<br>expected library, pcresolve=local |
| Kmeans.py:28:13 | `centres.copy()` | library / numpy | local / local | transitive_method | static_context | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=numpy pcresolve=local<br>expected library, pcresolve=local |
| Kmeans.py:39:15 | `D.argmin(axis=1)` | library / numpy | unknown / unknown | transitive_method | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:41:17 | `distances.mean()` | library / numpy | unknown / unknown | transitive_method | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:67:26 | `x.todense()` | library / scipy | python / python | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=python<br>owner mismatch: expected=scipy pcresolve=python<br>expected library, pcresolve=python |
| Kmeans.py:70:31 | `y.todense()` | library / scipy | python / python | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=python<br>owner mismatch: expected=scipy pcresolve=python<br>expected library, pcresolve=python |
| Kmeans.py:74:32 | `x.todense()` | library / scipy | python / python | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=python<br>owner mismatch: expected=scipy pcresolve=python<br>expected library, pcresolve=python |
| Kmeans.py:74:45 | `y.todense()` | library / scipy | python / python | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=python<br>owner mismatch: expected=scipy pcresolve=python<br>expected library, pcresolve=python |
| Kmeans.py:86:11 | `D.argmin(axis=1)` | library / numpy | library / scipy | transitive_method | dynamic_probe | owner mismatch: expected=numpy pcresolve=scipy |
