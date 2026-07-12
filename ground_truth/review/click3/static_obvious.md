# click3 — static_obvious (4 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| click_decorator.py:10:11 | `click.echo(f'Hello, {name}!')` | library / click | library / click | - | static_obvious | v: direct import-backed API call |
| click_decorator.py:5:1 | `click.command()` | library / click | library / click | - | static_obvious | v: direct import-backed API call |
| click_decorator.py:7:1 | `click.option('--name', prompt='Your name', help='The person to gree...` | library / click | library / click | - | static_obvious | v: direct import-backed API call |
| click_decorator.py:15:4 | `hello.main(standalone_mode=False)` | local / local | local / local | - | static_obvious | v: project-local function/method call |
