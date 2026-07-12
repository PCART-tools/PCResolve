# click1 — static_obvious (4 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| click_decorator.py:6:4 | `print(1)` | python / python | python / python | builtin | static_obvious | gt: Python builtin print()<br>v: Python builtin function call |
| click_decorator.py:7:4 | `click.echo(f'Hello, {name}!')` | library / click | library / click | direct_import | static_obvious | gt: Direct click.echo() call<br>v: direct import-backed API call |
| click_decorator.py:3:1 | `click.command()` | library / click | library / click | decorator_expression | static_obvious | gt: @click.command() decorator expression call<br>v: decorator expression is import-backed usage |
| click_decorator.py:4:1 | `click.option('--name', default='World', help='The person to greet.')` | library / click | library / click | decorator_expression | static_obvious | gt: @click.option(...) decorator expression call<br>v: decorator expression is import-backed usage |
