# redis — dynamic_probe (20 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| with_pattern.py:20:40 | `r.ping()` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client ping command<br>v: inspect.getmodule(r.ping) reports redis.commands.core |
| with_pattern.py:23:16 | `r.set('weather', 'sunny', ex=3600)` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client set command<br>v: inspect.getmodule(r.set) reports redis.commands.core |
| with_pattern.py:24:42 | `r.get('weather')` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client get command<br>v: inspect.getmodule(r.get) reports redis.commands.core |
| with_pattern.py:28:16 | `r.hset(user_id, mapping={'name': 'Alice', 'age': '25'})` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client hset command<br>v: inspect.getmodule(r.hset) reports redis.commands.core |
| with_pattern.py:29:36 | `r.hgetall(user_id)` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client hgetall command<br>v: inspect.getmodule(r.hgetall) reports redis.commands.core |
| with_pattern.py:32:16 | `r.lpush('recent_visitors', 'Alice', 'Bob', 'Charlie')` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client lpush command<br>v: inspect.getmodule(r.lpush) reports redis.commands.core |
| with_pattern.py:33:42 | `r.lrange('recent_visitors', 0, -1)` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client lrange command<br>v: inspect.getmodule(r.lrange) reports redis.commands.core |
| with_pattern.py:36:16 | `r.sadd('unique_visitors', 'Alice', 'Bob', 'Alice', 'Dave')` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client sadd command<br>v: inspect.getmodule(r.sadd) reports redis.commands.core |
| with_pattern.py:37:42 | `r.smembers('unique_visitors')` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client smembers command<br>v: inspect.getmodule(r.smembers) reports redis.commands.core |
| with_pattern.py:40:16 | `r.zadd('player_scores', {'Alice': 100, 'Bob': 85, 'Charlie': 95})` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client zadd command<br>v: inspect.getmodule(r.zadd) reports redis.commands.core |
| with_pattern.py:41:38 | `r.zrevrange('player_scores', 0, 1, withscores=True)` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client zrevrange command<br>v: inspect.getmodule(r.zrevrange) reports redis.commands.core |
| with_pattern.py:44:21 | `r.pipeline()` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client pipeline factory<br>v: inspect.getmodule(r.pipeline) reports redis.client |
| with_pattern.py:45:20 | `pipe.incr('page_views')` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis pipeline incr command<br>v: inspect.getmodule(pipe.incr) reports redis.commands.core |
| with_pattern.py:46:20 | `pipe.get('weather')` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis pipeline get command<br>v: inspect.getmodule(pipe.get) reports redis.commands.core |
| with_pattern.py:47:20 | `pipe.hgetall(user_id)` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis pipeline hgetall command<br>v: inspect.getmodule(pipe.hgetall) reports redis.commands.core |
| with_pattern.py:48:29 | `pipe.execute()` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis pipeline execute method<br>v: inspect.getmodule(pipe.execute) reports redis.client |
| with_pattern.py:52:25 | `r.pubsub()` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis PubSub factory<br>v: inspect.getmodule(r.pubsub) reports redis.client |
| with_pattern.py:53:16 | `pubsub.subscribe('news')` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis PubSub subscribe method<br>v: inspect.getmodule(pubsub.subscribe) reports redis.client |
| with_pattern.py:54:16 | `r.publish('news', 'Breaking news: Redis is awesome!')` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis client publish command<br>v: inspect.getmodule(r.publish) reports redis.commands.core |
| with_pattern.py:55:26 | `pubsub.get_message(timeout=1)` | library / redis | library / redis | transitive_method | dynamic_probe | gt: Redis PubSub get_message method<br>v: inspect.getmodule(pubsub.get_message) reports redis.client |
