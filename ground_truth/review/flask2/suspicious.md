# flask2 — Suspicious Records (7)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| app.py:66:27 | `request.json.get('description', '')` | python / python | library / flask | mapping_protocol_method | static_context | kind mismatch: expected=python pcresolve=library<br>owner mismatch: expected=python pcresolve=flask |
| app.py:69:8 | `tasks.append(task)` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| app.py:83:24 | `request.json.get('title', task['title'])` | python / python | library / flask | mapping_protocol_method | static_context | kind mismatch: expected=python pcresolve=library<br>owner mismatch: expected=python pcresolve=flask |
| app.py:84:30 | `request.json.get('description', task['description'])` | python / python | library / flask | mapping_protocol_method | static_context | kind mismatch: expected=python pcresolve=library<br>owner mismatch: expected=python pcresolve=flask |
| app.py:85:23 | `request.json.get('done', task['done'])` | python / python | library / flask | mapping_protocol_method | static_context | kind mismatch: expected=python pcresolve=library<br>owner mismatch: expected=python pcresolve=flask |
| app.py:103:22 | `getattr(error, 'description', None)` | python / python | local / local | builtin | static_obvious | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| app.py:105:26 | `error_messages.get(error.code, str(error))` | python / python | local / local | builtin_method_local_receiver | static_context | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
