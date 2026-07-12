# Youtube — Suspicious Records (8)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| Kmeans.py:27:14 | `centres.todense()` | library / scipy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=scipy pcresolve=local<br>expected library, pcresolve=local |
| Kmeans.py:28:13 | `centres.copy()` | library / numpy | local / local | transitive_method | static_context | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=numpy pcresolve=local<br>expected library, pcresolve=local |
| Kmeans.py:39:15 | `D.argmin(axis=1)` | library / numpy | unknown / unknown | transitive_method | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:41:17 | `distances.mean()` | library / numpy | unknown / unknown | transitive_method | static_context | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:67:26 | `x.todense()` | library / scipy | python / python | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=python<br>owner mismatch: expected=scipy pcresolve=python<br>expected library, pcresolve=python |
| Kmeans.py:70:31 | `y.todense()` | library / scipy | python / python | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=python<br>owner mismatch: expected=scipy pcresolve=python<br>expected library, pcresolve=python |
| Kmeans.py:74:32 | `x.todense()` | library / scipy | python / python | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=python<br>owner mismatch: expected=scipy pcresolve=python<br>expected library, pcresolve=python |
| Kmeans.py:74:45 | `y.todense()` | library / scipy | python / python | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=python<br>owner mismatch: expected=scipy pcresolve=python<br>expected library, pcresolve=python |
