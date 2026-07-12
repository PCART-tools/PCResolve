# mysql — static_context (8 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| with_pattern.py:17:17 | `conn.cursor(dictionary=True)` | library / mysql | library / mysql | - | static_context | v: receiver conn from mysql.connector.connect() return; pcresolve propagates via RE |
| with_pattern.py:20:20 | `cursor.execute('\n                        CREATE TABLE IF NOT EXIST...` | library / mysql | library / mysql | - | static_context | v: receiver cursor from conn.cursor() return; type is mysql.connector.cursor |
| with_pattern.py:36:20 | `cursor.executemany('INSERT INTO products (name, price) VALUES (%s, ...` | library / mysql | library / mysql | - | static_context | v: receiver cursor from conn.cursor() return; type is mysql.connector.cursor |
| with_pattern.py:43:20 | `conn.commit()` | library / mysql | library / mysql | - | static_context | v: receiver conn from mysql.connector.connect() return; type is mysql.connector.con |
| with_pattern.py:48:20 | `cursor.execute('SELECT * FROM products')` | library / mysql | library / mysql | - | static_context | v: receiver cursor from conn.cursor() return; type is mysql.connector.cursor |
| with_pattern.py:54:20 | `cursor.execute('SELECT * FROM products WHERE price < %s', (50,))` | library / mysql | library / mysql | - | static_context | v: receiver cursor from conn.cursor() return; type is mysql.connector.cursor |
| with_pattern.py:60:20 | `conn.rollback()` | library / mysql | library / mysql | - | static_context | v: receiver conn from mysql.connector.connect() return; type is mysql.connector.con |
| with_pattern.py:63:20 | `conn.rollback()` | library / mysql | library / mysql | - | static_context | v: receiver conn from mysql.connector.connect() return; type is mysql.connector.con |
