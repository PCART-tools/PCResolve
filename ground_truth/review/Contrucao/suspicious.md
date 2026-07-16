# Contrucao — Suspicious Records (6)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| main.py:18:9 | `letra.isalpha()` | python / python | local / local | builtin_string_method | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| main.py:19:18 | `palavra.replace(letra, '')` | python / python | local / local | builtin_string_method | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| main.py:50:17 | `sentence.split()` | python / python | local / local | builtin_string_method | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| main.py:51:29 | `palavra.strip()` | python / python | local / local | builtin_string_method | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| main.py:73:17 | `sentence.split()` | python / python | local / local | builtin_string_method | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| main.py:74:27 | `palavra.strip()` | python / python | local / local | builtin_string_method | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
