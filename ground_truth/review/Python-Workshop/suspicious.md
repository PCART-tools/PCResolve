# Python-Workshop — Suspicious Records (2)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| myregr.py:16:11 | `res.dot(res)` | library / numpy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
| myregr.py:24:17 | `dif.dot(xp)` | library / numpy | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=numpy pcresolve=unknown<br>expected library, pcresolve=unknown |
