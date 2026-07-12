# django — Suspicious Records (1)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| proxy.py:109:14 | `"{}".format(msg.format(*args, **kwargs))` | python / python |  /  | builtin | static_obvious | manual_gt<br>pcresolve missing candidate: expected=python/python |
