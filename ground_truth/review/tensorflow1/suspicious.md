# tensorflow1 — Suspicious Records (1)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| tf_decorator.py:19:8 | `config.update({'units': self.units})` | python / python | unknown / unknown | builtin | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
