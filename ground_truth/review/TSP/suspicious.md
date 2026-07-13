# TSP — Suspicious Records (2)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| ctfds.py:36:12 | `hamiltonianPath.append(u)` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| ctfds.py:42:4 | `hamiltonianPath.append(hamiltonianPath[0])` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
