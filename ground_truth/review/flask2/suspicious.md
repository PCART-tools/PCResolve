# flask2 — Suspicious Records (4)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| app.py:66:27 | `request.json.get('description', '')` | python / python | unknown / unknown | mapping_protocol_method | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| app.py:83:24 | `request.json.get('title', task['title'])` | python / python | unknown / unknown | mapping_protocol_method | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| app.py:84:30 | `request.json.get('description', task['description'])` | python / python | unknown / unknown | mapping_protocol_method | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| app.py:85:23 | `request.json.get('done', task['done'])` | python / python | unknown / unknown | mapping_protocol_method | static_context | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
