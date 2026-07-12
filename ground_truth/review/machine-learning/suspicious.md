# machine-learning — Suspicious Records (2)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| sci.py:23:10 | `uarr.dot(sarr)` | library / numpy | library / scipy | transitive_method | dynamic_probe | owner mismatch: expected=numpy pcresolve=scipy |
| sci.py:23:10 | `uarr.dot(sarr).dot(vharr)` | library / numpy | library / scipy | transitive_method | dynamic_probe | owner mismatch: expected=numpy pcresolve=scipy |
