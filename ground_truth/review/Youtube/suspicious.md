# Youtube — Suspicious Records (6)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| Kmeans.py:39:15 | `D.argmin(axis=1)` | library / numpy | unknown / unknown | transitive_method | static_context | kind mismatch: expected=library pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:41:17 | `distances.mean()` | library / numpy | unknown / unknown | transitive_method | static_context | kind mismatch: expected=library pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:67:26 | `x.todense()` | library / scipy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=scipy pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:70:31 | `y.todense()` | library / scipy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=scipy pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:74:32 | `x.todense()` | library / scipy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=scipy pcresolve=unknown<br>expected library, pcresolve=unknown |
| Kmeans.py:74:45 | `y.todense()` | library / scipy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=scipy pcresolve=unknown<br>expected library, pcresolve=unknown |
