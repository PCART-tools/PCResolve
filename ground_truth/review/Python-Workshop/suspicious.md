# Python-Workshop — Suspicious Records (4)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| myregr.py:16:11 | `res.dot(res)` | library / numpy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=numpy pcresolve=local<br>expected library, pcresolve=local |
| myregr.py:24:17 | `dif.dot(xp)` | library / numpy | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=numpy pcresolve=local<br>expected library, pcresolve=local |
| myregr.py:37:8 | `s.append(c.x)` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| skregr.py:14:8 | `s.append(model.coef_)` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
