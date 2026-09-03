# mysql — static_obvious (13 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| with_pattern.py:15:13 | `mysql.connector.connect(**db_config)` | library / mysql | library / mysql | - | static_obvious | v: import-backed dotted module call |
| with_pattern.py:27:20 | `print("Table 'products' created/verified successfully")` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:40:20 | `print(f'Inserted {cursor.rowcount} records')` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:44:20 | `print('Transaction committed')` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:47:20 | `print('\nAll products:')` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:50:24 | `print(f"ID: {row['id']}, Name: {row['name']}, Price: {row['price']}")` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:53:20 | `print('\nProducts under $50:')` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:56:24 | `print(f"{row['name']}: ${row['price']}")` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:61:20 | `print(f'Database error occurred: {e}')` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:64:20 | `print(f'Unexpected error: {e}')` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:67:8 | `print(f'Failed to connect to MySQL: {e}')` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:69:8 | `print(f'General error occurred: {e}')` | python / python | python / python | - | static_obvious | v: Python builtin function or method call |
| with_pattern.py:73:4 | `main()` | local / local | local / local | - | static_obvious | v: project-local function/method call |
