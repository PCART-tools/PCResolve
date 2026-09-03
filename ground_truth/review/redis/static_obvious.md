# redis — static_obvious (13 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| with_pattern.py:12:13 | `redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_r...` | library / redis | library / redis | direct_import | static_obvious | v: direct import-backed API call |
| with_pattern.py:20:16 | `print(f'PING response: {r.ping()}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:24:16 | `print(f"Current weather: {r.get('weather')}")` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:29:16 | `print(f'User data: {r.hgetall(user_id)}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:33:16 | `print(f"Recent visitors: {r.lrange('recent_visitors', 0, -1)}")` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:37:16 | `print(f"Unique visitors: {r.smembers('unique_visitors')}")` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:41:16 | `print(f"Top players: {r.zrevrange('player_scores', 0, 1, withscores...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:49:20 | `print(f'Transaction results - Page views: {result[0]}, Weather: {re...` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:57:20 | `print(f'Received message: {message}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:60:16 | `print(f'Redis operation failed: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:63:8 | `print(f'Failed to connect to Redis: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:65:8 | `print(f'Unexpected error: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:68:4 | `main()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
