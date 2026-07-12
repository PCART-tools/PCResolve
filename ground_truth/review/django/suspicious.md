# django — Suspicious Records (9)

Each record appears once.  The **Reasons** column lists all
matching suspicious criteria.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Reasons |
|---------------|------------|----|-----------|----------|-------|---------|
| proxy.py:30:4 | `stream.read_until(delimiter, cb)` | library / tornado | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=tornado pcresolve=local<br>expected library, pcresolve=local |
| proxy.py:93:22 | `line.split()` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| proxy.py:97:25 | `obj[3].split('/')` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| proxy.py:109:14 | `"{}".format(msg.format(*args, **kwargs))` | python / python |  /  | builtin | static_obvious | manual_gt<br>pcresolve missing candidate: expected=python/python |
| proxy.py:109:26 | `msg.format(*args, **kwargs)` | python / python | local / local | builtin_method_local_receiver | dynamic_probe | kind mismatch: expected=python pcresolve=local<br>owner mismatch: expected=python pcresolve=local |
| proxy.py:129:8 | `stream.set_close_callback(conn.on_disconnect)` | library / tornado | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=tornado pcresolve=local<br>expected library, pcresolve=local |
| proxy.py:130:8 | `stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_N...` | library / socket | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=socket pcresolve=local<br>expected library, pcresolve=local |
| proxy.py:131:8 | `stream.socket.setsockopt(socket.IPPROTO_TCP, socket.SO_KE...` | library / socket | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=socket pcresolve=local<br>expected library, pcresolve=local |
| proxy.py:143:4 | `server.listen(8889)` | library / tornado | local / local | transitive_method | dynamic_probe | kind mismatch: expected=library pcresolve=local<br>owner mismatch: expected=tornado pcresolve=local<br>expected library, pcresolve=local |
