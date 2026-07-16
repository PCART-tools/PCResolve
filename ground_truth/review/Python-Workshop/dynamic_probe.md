# Python-Workshop — dynamic_probe (7 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| myregr.py:15:10 | `pol(x)` | library / numpy | library / numpy | transitive_method | dynamic_probe | v: runtime probe: callable type is numpy.poly1d, implementation is numpy.lib.polyno |
| myregr.py:16:11 | `res.dot(res)` | library / numpy | local / local | transitive_method | dynamic_probe | v: runtime probe: receiver type is numpy.ndarray; dot is bound and its descriptor o |
| myregr.py:20:15 | `pol(x)` | library / numpy | library / numpy | transitive_method | dynamic_probe | v: runtime probe: callable type is numpy.poly1d, implementation is numpy.lib.polyno |
| myregr.py:24:17 | `dif.dot(xp)` | library / numpy | local / local | transitive_method | dynamic_probe | v: runtime probe: receiver type is numpy.ndarray; dot is bound and its descriptor o |
| myregr.py:37:8 | `s.append(c.x)` | python / python | python / python | builtin_method_local_receiver | dynamic_probe | v: runtime probe: receiver type is builtins.list; append is bound and its descripto |
| myregr.py:43:29 | `pol(x)` | library / numpy | library / numpy | transitive_method | dynamic_probe | v: runtime probe: callable type is numpy.poly1d, implementation is numpy.lib.polyno |
| skregr.py:14:8 | `s.append(model.coef_)` | python / python | python / python | builtin_method_local_receiver | dynamic_probe | v: runtime probe: receiver type is builtins.list; append is bound and its descripto |
