# psycopg2 — Needs Annotation (19 records)

These records do not yet have `verification_level` or 
`expected_*` fields confirmed by a human annotator.

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| with_pattern.py:22:17 | `conn.cursor(cursor_factory=DictCursor)` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:25:20 | `cursor.execute('\n                        DROP TABLE IF EXISTS empl...` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:52:24 | `cursor.execute(insert_query, emp)` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:53:33 | `cursor.fetchone()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:57:20 | `cursor.execute('\n                        UPDATE employees \n      ...` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:66:20 | `cursor.execute('SELECT * FROM employees ORDER BY salary DESC')` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:68:31 | `cursor.fetchall()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:72:20 | `cursor.execute('\n                        SELECT name, salary \n   ...` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:78:31 | `cursor.fetchall()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:82:20 | `conn.commit()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:86:20 | `conn.rollback()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:89:20 | `conn.rollback()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:92:20 | `conn.rollback()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:97:17 | `conn.cursor()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:99:20 | `cursor.execute('DELETE FROM employees WHERE name = %s', ('Mike John...` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:103:20 | `cursor.execute('SELECT COUNT(*) FROM employees WHERE name = %s', ('...` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:104:28 | `cursor.fetchone()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:107:20 | `conn.commit()` |  /  | library / psycopg2 | - | - |  |
| with_pattern.py:109:20 | `conn.rollback()` |  /  | library / psycopg2 | - | - |  |
