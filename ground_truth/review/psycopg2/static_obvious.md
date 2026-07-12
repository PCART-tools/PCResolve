# psycopg2 — static_obvious (20 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| with_pattern.py:17:13 | `psycopg2.connect(**db_params)` | library / psycopg2 | library / psycopg2 | direct_import | static_obvious | v: direct import-backed API call |
| with_pattern.py:36:20 | `print('Table created successfully')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:39:35 | `sql.SQL('\n                        INSERT INTO employees (name, dep...` | library / psycopg2 | library / psycopg2 | direct_import | static_obvious | v: direct import-backed API call |
| with_pattern.py:54:24 | `print(f'Inserted employee {emp[0]}, ID: {emp_id}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:62:20 | `print(f'Updated {cursor.rowcount} records')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:67:20 | `print('\nAll employees (sorted by salary descending):')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:69:24 | `print(dict(row))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:69:30 | `dict(row)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:77:20 | `print('\nEmployees with salary above 8000:')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:79:24 | `print(f"{row['name']}: {row['salary']}")` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:83:20 | `print('\nTransaction committed')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:87:20 | `print(f'Unique constraint violation: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:90:20 | `print(f'Database error: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:93:20 | `print(f'Error occurred: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:100:20 | `print(f'\nDeleted {cursor.rowcount} records')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:105:20 | `print(f'Records count for Mike Johnson after deletion: {count}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:110:20 | `print(f'Delete operation failed: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:113:8 | `print(f'Failed to connect to database: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:115:8 | `print(f'Error occurred: {e}')` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| with_pattern.py:120:4 | `main()` | local / local | local / local | local_call | static_obvious | v: project-local function/method call |
