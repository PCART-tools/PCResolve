# aiofiles1 — static_context (2 records)

| File:Line:Col | Expression | GT | PCResolve | Category | Level | Notes |
|---------------|------------|----|-----------|----------|-------|-------|
| async_pattern.py:6:14 | `f.write('Hello, world!')` | library / aiofiles | library / aiofiles | - | static_context | v: receiver f from aiofiles.open() context manager; pcresolve propagates via RETURN |
| async_pattern.py:9:24 | `f.read()` | library / aiofiles | library / aiofiles | - | static_context | v: receiver f from aiofiles.open() context manager; pcresolve propagates via RETURN |
