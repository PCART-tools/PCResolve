# django — static_obvious (27 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| proxy.py:27:43 | `itertools.count()` | library / itertools | library / itertools | direct_import | static_obvious | v: direct import-backed API call |
| proxy.py:28:12 | `next(_idalloc)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| proxy.py:29:15 | `tornado.gen.Callback(cb_id)` | library / tornado | library / tornado | direct_import | static_obvious | v: import-backed dotted module call: tornado.gen.Callback |
| proxy.py:31:19 | `tornado.gen.Wait(cb_id)` | library / tornado | library / tornado | direct_import | static_obvious | v: import-backed dotted module call: tornado.gen.Wait |
| proxy.py:32:10 | `tornado.gen.Return(result)` | library / tornado | library / tornado | direct_import | static_obvious | v: import-backed dotted module call: tornado.gen.Return |
| proxy.py:35:11 | `tornado.gen.Task(stream.write, data)` | library / tornado | library / tornado | direct_import | static_obvious | v: import-backed dotted module call: tornado.gen.Task |
| proxy.py:47:17 | `redis.StrictRedis(host=self.REDIS_HOST, port=self.REDIS_PORT, db=0)` | library / redis | library / redis | direct_import | static_obvious | v: direct import-backed API call |
| proxy.py:57:34 | `str(status)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| proxy.py:57:51 | `str(scope.session)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| proxy.py:57:71 | `time.time()` | library / time | library / time | direct_import | static_obvious | v: direct import-backed API call |
| proxy.py:57:84 | `json.dumps(request)` | library / json | library / json | direct_import | static_obvious | v: direct import-backed API call |
| proxy.py:62:8 | `self.set_expire()` | local / local | local / local | local_call | static_obvious | gt: Project-local Scope.set_expire method<br>v: set_expire is defined on project-local class Scope |
| proxy.py:66:8 | `self.set_expire()` | local / local | local / local | local_call | static_obvious | gt: Project-local Scope.set_expire method<br>v: set_expire is defined on project-local class Scope |
| proxy.py:69:36 | `str(self.session)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| proxy.py:71:8 | `Scope()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| proxy.py:92:29 | `read_until(self.stream, '\n')` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| proxy.py:109:8 | `print('{}'.format(msg.format(*args, **kwargs)))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| proxy.py:109:14 | `"{}".format(msg.format(*args, **kwargs))` | python / python |  /  | builtin | static_obvious | gt: PCResolve missed literal str.format()<br>v: literal str.format(); call-collection gap |
| proxy.py:119:8 | `tornado.tcpserver.TCPServer.__init__(self, io_loop=io_loop, ssl_opt...` | library / tornado | library / tornado | direct_import | static_obvious | v: import-backed dotted module call: tornado.tcpserver.TCPServer.__init__ |
| proxy.py:122:31 | `itertools.count(1)` | library / itertools | library / itertools | direct_import | static_obvious | v: direct import-backed API call |
| proxy.py:128:15 | `SimpleEcho()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| proxy.py:138:10 | `Exception('debuging...finished!')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| proxy.py:142:13 | `SimpleEchoServer()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
| proxy.py:148:4 | `signal.signal(signal.SIGALRM, timeout_handler)` | library / signal | library / signal | direct_import | static_obvious | v: direct import-backed API call |
| proxy.py:150:4 | `signal.alarm(5)` | library / signal | library / signal | direct_import | static_obvious | v: direct import-backed API call |
| proxy.py:153:5 | `tornado.ioloop.IOLoop.instance()` | library / tornado | library / tornado | direct_import | static_obvious | v: import-backed dotted module call: tornado.ioloop.IOLoop.instance |
| proxy.py:155:8 | `print(e)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
