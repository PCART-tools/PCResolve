# redis — Needs Annotation (20 records)

These records do not yet have `verification_level` or 
`expected_*` fields confirmed by a human annotator.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| with_pattern.py:20:40 | `r.ping()` |  /  | library / redis | - | - |  |
| with_pattern.py:23:16 | `r.set('weather', 'sunny', ex=3600)` |  /  | library / redis | - | - |  |
| with_pattern.py:24:42 | `r.get('weather')` |  /  | library / redis | - | - |  |
| with_pattern.py:28:16 | `r.hset(user_id, mapping={'name': 'Alice', 'age': '25'})` |  /  | library / redis | - | - |  |
| with_pattern.py:29:36 | `r.hgetall(user_id)` |  /  | library / redis | - | - |  |
| with_pattern.py:32:16 | `r.lpush('recent_visitors', 'Alice', 'Bob', 'Charlie')` |  /  | library / redis | - | - |  |
| with_pattern.py:33:42 | `r.lrange('recent_visitors', 0, -1)` |  /  | library / redis | - | - |  |
| with_pattern.py:36:16 | `r.sadd('unique_visitors', 'Alice', 'Bob', 'Alice', 'Dave')` |  /  | library / redis | - | - |  |
| with_pattern.py:37:42 | `r.smembers('unique_visitors')` |  /  | library / redis | - | - |  |
| with_pattern.py:40:16 | `r.zadd('player_scores', {'Alice': 100, 'Bob': 85, 'Charlie': 95})` |  /  | library / redis | - | - |  |
| with_pattern.py:41:38 | `r.zrevrange('player_scores', 0, 1, withscores=True)` |  /  | library / redis | - | - |  |
| with_pattern.py:44:21 | `r.pipeline()` |  /  | library / redis | - | - |  |
| with_pattern.py:45:20 | `pipe.incr('page_views')` |  /  | library / redis | - | - |  |
| with_pattern.py:46:20 | `pipe.get('weather')` |  /  | library / redis | - | - |  |
| with_pattern.py:47:20 | `pipe.hgetall(user_id)` |  /  | library / redis | - | - |  |
| with_pattern.py:48:29 | `pipe.execute()` |  /  | library / redis | - | - |  |
| with_pattern.py:52:25 | `r.pubsub()` |  /  | library / redis | - | - |  |
| with_pattern.py:53:16 | `pubsub.subscribe('news')` |  /  | library / redis | - | - |  |
| with_pattern.py:54:16 | `r.publish('news', 'Breaking news: Redis is awesome!')` |  /  | library / redis | - | - |  |
| with_pattern.py:55:26 | `pubsub.get_message(timeout=1)` |  /  | library / redis | - | - |  |
