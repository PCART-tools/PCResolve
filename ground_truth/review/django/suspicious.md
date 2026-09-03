# django — Suspicious Records (7)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| proxy.py:30:4 | `stream.read_until(delimiter, cb)` | library / tornado | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=tornado pcresolve=unknown<br>expected library, pcresolve=unknown |
| proxy.py:93:22 | `line.split()` | python / python | unknown / unknown | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| proxy.py:97:25 | `obj[3].split('/')` | python / python | unknown / unknown | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| proxy.py:109:26 | `msg.format(*args, **kwargs)` | python / python | unknown / unknown | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=unknown<br>owner mismatch: expected=python pcresolve=unknown |
| proxy.py:129:8 | `stream.set_close_callback(conn.on_disconnect)` | library / tornado | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=tornado pcresolve=unknown<br>expected library, pcresolve=unknown |
| proxy.py:130:8 | `stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_N...` | library / socket | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=socket pcresolve=unknown<br>expected library, pcresolve=unknown |
| proxy.py:131:8 | `stream.socket.setsockopt(socket.IPPROTO_TCP, socket.SO_KE...` | library / socket | unknown / unknown | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=unknown<br>owner mismatch: expected=socket pcresolve=unknown<br>expected library, pcresolve=unknown |
