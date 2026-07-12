# django — Needs Annotation (18 records)

These records do not yet have `verification_level` or 
`expected_*` fields confirmed by a human annotator.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| proxy.py:30:4 | `stream.read_until(delimiter, cb)` |  /  | local / local | - | - |  |
| proxy.py:49:8 | `self.r.set(self.key, self.session)` |  /  | library / redis | - | - |  |
| proxy.py:51:8 | `self.set_expire()` |  /  | library / redis | - | - |  |
| proxy.py:57:8 | `self.r.zadd(self.key + '::' + str(status) + '::' + str(scope.sessio...` |  /  | library / redis | - | - |  |
| proxy.py:61:8 | `self.r.set(self.key, self.session)` |  /  | library / redis | - | - |  |
| proxy.py:62:8 | `self.set_expire()` |  /  | library / redis | - | - |  |
| proxy.py:66:8 | `self.set_expire()` |  /  | library / redis | - | - |  |
| proxy.py:69:8 | `self.r.expire(self.key + '::' + str(self.session), self.timeout)` |  /  | library / redis | - | - |  |
| proxy.py:80:14 | `self.dispatch()` |  /  | local / local | - | - |  |
| proxy.py:93:22 | `line.split()` |  /  | local / local | - | - |  |
| proxy.py:97:25 | `obj[3].split('/')` |  /  | local / local | - | - |  |
| proxy.py:99:16 | `scope.add_request(status[1], request)` |  /  | library / redis | - | - |  |
| proxy.py:109:26 | `msg.format(*args, **kwargs)` |  /  | local / local | - | - |  |
| proxy.py:129:8 | `stream.set_close_callback(conn.on_disconnect)` |  /  | local / local | - | - |  |
| proxy.py:130:8 | `stream.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)` |  /  | local / local | - | - |  |
| proxy.py:131:8 | `stream.socket.setsockopt(socket.IPPROTO_TCP, socket.SO_KEEPALIVE, 1)` |  /  | local / local | - | - |  |
| proxy.py:133:14 | `conn.on_connect()` |  /  | local / local | - | - |  |
| proxy.py:143:4 | `server.listen(8889)` |  /  | local / local | - | - |  |
