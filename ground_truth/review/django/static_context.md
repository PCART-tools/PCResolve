# django — static_context (2 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| proxy.py:61:8 | `self.r.set(self.key, self.session)` | library / redis | library / redis | transitive_method | static_context | gt: Redis StrictRedis set method<br>v: self.r is initialized as redis.StrictRedis; the same bound set method was confir |
| proxy.py:153:5 | `tornado.ioloop.IOLoop.instance().start()` | library / tornado | library / tornado | transitive_method | static_context | v: import-backed dotted module call: tornado.ioloop.IOLoop.instance().start |
