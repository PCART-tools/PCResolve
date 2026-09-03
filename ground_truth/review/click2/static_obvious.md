# click2 — static_obvious (7 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| click_decorator.py:9:13 | `range(count)` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| click_decorator.py:10:8 | `click.echo(f'Hello, {name}!')` | library / click | library / click | direct_import | static_obvious | v: direct import-backed API call |
| click_decorator.py:4:1 | `click.command()` | library / click | library / click | direct_import | static_obvious | v: direct import-backed API call |
| click_decorator.py:5:1 | `click.option('--count', default=1, help='Number of greetings.')` | library / click | library / click | direct_import | static_obvious | v: direct import-backed API call |
| click_decorator.py:6:1 | `click.option('--name', prompt='Your name', help='The person to gree...` | library / click | library / click | direct_import | static_obvious | v: direct import-backed API call |
| click_decorator.py:15:4 | `print(inspect.signature(hello))` | python / python | python / python | builtin | static_obvious | v: Python builtin function or method call |
| click_decorator.py:15:10 | `inspect.signature(hello)` | library / inspect | library / inspect | direct_import | static_obvious | v: direct import-backed API call |
